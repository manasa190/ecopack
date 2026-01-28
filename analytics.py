import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import io
import json

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

from models import Recommendation, Material

analytics_bp = Blueprint("analytics", __name__)


# ================= JSON SAFE CONVERTER ================= #
def make_json_safe(obj):
    """Convert numpy/pandas objects to JSON-serializable types"""
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.floating, float)):
        if pd.isna(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


# ================= DASHBOARD DATA ================= #
@analytics_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    try:
        user_id = int(get_jwt_identity())
        
        # Get user's recommendations
        recs = Recommendation.query.filter_by(user_id=user_id).all()
        
        if not recs:
            # Return empty structure for new users
            return jsonify({
                "metrics": {
                    "total_recommendations": 0,
                    "avg_co2_reduction": 0.0,
                    "avg_cost_savings": 0.0,
                    "avg_eco_score": 0.0,
                    "top_material": "None",
                    "total_co2_saved": 0.0,
                    "total_cost_saved": 0.0
                },
                "charts": {}
            }), 200
        
        # Prepare data
        data = []
        for rec in recs:
            if rec.material:
                data.append({
                    "material": rec.material.material_name,
                    "co2": float(rec.co2_reduction_percent or 0),
                    "cost": float(rec.cost_savings_percent or 0),
                    "score": float(rec.recommendation_score or 0),
                    "date": rec.created_at
                })
        
        if not data:
            return jsonify({
                "metrics": {
                    "total_recommendations": 0,
                    "avg_co2_reduction": 0.0,
                    "avg_cost_savings": 0.0,
                    "avg_eco_score": 0.0,
                    "top_material": "None",
                    "total_co2_saved": 0.0,
                    "total_cost_saved": 0.0
                },
                "charts": {}
            }), 200
        
        df = pd.DataFrame(data)
        
        # Calculate metrics
        total_recs = len(df)
        avg_co2 = round(df["co2"].mean(), 1)
        avg_cost = round(df["cost"].mean(), 1)
        avg_score = round(df["score"].mean(), 2)
        
        # Find top material
        material_counts = df["material"].value_counts()
        top_material = material_counts.index[0] if not material_counts.empty else "None"
        
        # Calculate totals (assuming each recommendation saves CO2/cost)
        total_co2_saved = round(df["co2"].sum() / 100 * total_recs, 1)  # Simplified calculation
        total_cost_saved = round(df["cost"].sum() / 100 * total_recs * 100, 1)  # Assuming $100 per product
        
        metrics = {
            "total_recommendations": total_recs,
            "avg_co2_reduction": avg_co2,
            "avg_cost_savings": avg_cost,
            "avg_eco_score": avg_score,
            "top_material": top_material,
            "total_co2_saved": total_co2_saved,
            "total_cost_saved": total_cost_saved
        }
        
        # Create charts
        charts = create_charts(df)
        
        # Get recent recommendations for activity list
        recent_recs = []
        for rec in recs[-5:]: # Last 5
            recent_recs.append({
                "id": rec.id,
                "product": rec.product.product_name if rec.product else "Unknown",
                "material": rec.material.material_name if rec.material else "Unknown",
                "score": float(rec.recommendation_score or 0),
                "date": rec.created_at.isoformat()
            })
        recent_recs.reverse() # Newest first

        return jsonify({
            "metrics": metrics,
            "charts": make_json_safe(charts),
            "recent_recommendations": recent_recs
        }), 200
        
    except Exception as e:
        print(f"❌ Dashboard error: {str(e)}")
        return jsonify({"error": f"Failed to load dashboard: {str(e)}"}), 500


def create_charts(df):
    """Create Plotly charts from dataframe"""
    display_charts = {}
    
    # 1. Monthly Trends Chart
    try:
        df["month"] = df["date"].dt.strftime("%Y-%m")
        monthly_data = df.groupby("month").agg({
            "co2": "mean",
            "cost": "mean",
            "score": "mean"
        }).reset_index().sort_values("month")
        
        if not monthly_data.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=monthly_data["month"], y=monthly_data["co2"],
                mode="lines+markers", name="CO₂ Reduction",
                line=dict(color="#10B981", width=3)
            ))
            fig_trend.add_trace(go.Scatter(
                x=monthly_data["month"], y=monthly_data["cost"],
                mode="lines+markers", name="Cost Savings",
                line=dict(color="#3B82F6", width=3)
            ))
            fig_trend.update_layout(
                xaxis=dict(title="Month", type="category"),
                yaxis_title="Percentage (%)",
                template="plotly_white",
                margin=dict(l=50, r=20, t=20, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            display_charts["trend_chart"] = fig_trend.to_dict()
    except Exception as e:
        print(f"⚠️ Trend chart error: {e}")

    # 2. Material Usage Chart
    try:
        m_counts = df["material"].value_counts().head(8).reset_index()
        m_counts.columns = ["material", "count"]
        if not m_counts.empty:
            fig_mat = px.bar(
                m_counts, x="material", y="count",
                color="count", color_continuous_scale="Viridis"
            )
            fig_mat.update_layout(
                template="plotly_white",
                xaxis_title="Material",
                yaxis_title="Count",
                margin=dict(l=50, r=20, t=20, b=50),
                coloraxis_showscale=False
            )
            display_charts["material_chart"] = fig_mat.to_dict()
    except Exception as e:
        print(f"⚠️ Material chart error: {e}")

    # 3. Score Distribution
    try:
        if len(df) > 0:
            fig_hist = px.histogram(
                df, x="score", nbins=10,
                color_discrete_sequence=["#10B981"]
            )
            fig_hist.update_layout(
                template="plotly_white",
                xaxis_title="Eco Score",
                yaxis_title="Frequency",
                margin=dict(l=50, r=20, t=20, b=50)
            )
            display_charts["score_chart"] = fig_hist.to_dict()
    except Exception as e:
        print(f"⚠️ Score chart error: {e}")
    
    return display_charts


# ================= EXPORT CSV ================= #
@analytics_bp.route("/export/csv", methods=["GET"])
@jwt_required()
def export_csv():
    try:
        user_id = int(get_jwt_identity())
        recs = Recommendation.query.filter_by(user_id=user_id).all()
        
        data = []
        for rec in recs:
            data.append({
                "Material": rec.material.material_name if rec.material else "Unknown",
                "CO2 Reduction (%)": round(rec.co2_reduction_percent or 0, 2),
                "Cost Savings (%)": round(rec.cost_savings_percent or 0, 2),
                "Eco Score": round(rec.recommendation_score or 0, 3),
                "Date": rec.created_at.strftime("%Y-%m-%d %H:%M"),
                "Product": rec.product.product_name if rec.product else "Unknown"
            })
        
        df = pd.DataFrame(data)
        
        buf = io.BytesIO()
        df.to_csv(buf, index=False, encoding='utf-8')
        buf.seek(0)
        
        filename = f"EcoPackAI_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype="text/csv"
        )
        
    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


# ================= EXPORT EXCEL ================= #
@analytics_bp.route("/export/excel", methods=["GET"])
@jwt_required()
def export_excel():
    try:
        user_id = int(get_jwt_identity())
        recs = Recommendation.query.filter_by(user_id=user_id).all()
        
        data = []
        for rec in recs:
            data.append({
                "Material": rec.material.material_name if rec.material else "Unknown",
                "CO2 Reduction (%)": round(rec.co2_reduction_percent or 0, 2),
                "Cost Savings (%)": round(rec.cost_savings_percent or 0, 2),
                "Eco Score": round(rec.recommendation_score or 0, 3),
                "Date": rec.created_at.strftime("%Y-%m-%d %H:%M"),
                "Product": rec.product.product_name if rec.product else "Unknown",
                "Recyclability (%)": rec.material.recyclability_percent if rec.material else 0,
                "Strength": rec.material.strength_rating if rec.material else 0,
                "Cost per kg": rec.material.cost_per_kg if rec.material else 0
            })
        
        df = pd.DataFrame(data)
        
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Recommendations', index=False)
            
            # Add summary sheet
            if not df.empty:
                summary = {
                    "Metric": ["Total Recommendations", "Avg CO2 Reduction", "Avg Cost Savings", "Avg Eco Score"],
                    "Value": [
                        len(df),
                        f"{df['CO2 Reduction (%)'].mean():.1f}%",
                        f"{df['Cost Savings (%)'].mean():.1f}%",
                        f"{df['Eco Score'].mean():.3f}"
                    ]
                }
                summary_df = pd.DataFrame(summary)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        buf.seek(0)
        
        filename = f"EcoPackAI_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


# ================= EXPORT PDF ================= #
@analytics_bp.route("/export/pdf", methods=["GET"])
@jwt_required()
def export_pdf():
    try:
        user_id = int(get_jwt_identity())
        recs = Recommendation.query.filter_by(user_id=user_id).all()
        
        if not recs:
            return jsonify({"error": "No data to export"}), 400
        
        # Create PDF
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#198754"),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor("#0d6efd"),
            spaceAfter=10
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build document
        elements = []
        
        # Title
        elements.append(Paragraph("EcoPackAI Sustainability Report", title_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Summary
        elements.append(Paragraph("Executive Summary", header_style))
        
        if recs:
            avg_co2 = sum(r.co2_reduction_percent or 0 for r in recs) / len(recs)
            avg_cost = sum(r.cost_savings_percent or 0 for r in recs) / len(recs)
            avg_score = sum(r.recommendation_score or 0 for r in recs) / len(recs)
            
            summary_text = f"""
            Total Recommendations: {len(recs)}<br/>
            Average CO₂ Reduction: {avg_co2:.1f}%<br/>
            Average Cost Savings: {avg_cost:.1f}%<br/>
            Average Eco Score: {avg_score:.3f}<br/>
            Report Period: {min(r.created_at for r in recs).strftime('%Y-%m-%d')} to {max(r.created_at for r in recs).strftime('%Y-%m-%d')}
            """
            elements.append(Paragraph(summary_text, normal_style))
        
        elements.append(Spacer(1, 20))
        
        # Recommendations Table
        elements.append(Paragraph("Detailed Recommendations", header_style))
        
        table_data = [["Material", "CO₂ Reduction", "Cost Savings", "Eco Score", "Date", "Product"]]
        
        for rec in recs[:50]:  # Limit to first 50 records
            table_data.append([
                rec.material.material_name if rec.material else "Unknown",
                f"{rec.co2_reduction_percent or 0:.1f}%",
                f"{rec.cost_savings_percent or 0:.1f}%",
                f"{rec.recommendation_score or 0:.3f}",
                rec.created_at.strftime("%Y-%m-%d"),
                rec.product.product_name if rec.product else "Unknown"
            ])
        
        table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1*inch, 0.8*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#198754")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(table)
        
        if len(recs) > 50:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"... and {len(recs) - 50} more recommendations", normal_style))
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("EcoPackAI - Sustainable Packaging Solutions", styles['Italic']))
        elements.append(Paragraph("Generated with AI-powered recommendations", styles['Italic']))
        
        # Build PDF
        doc.build(elements)
        buf.seek(0)
        
        filename = f"EcoPackAI_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )
        
    except Exception as e:
        print(f"❌ PDF export error: {str(e)}")
        return jsonify({"error": f"PDF export failed: {str(e)}"}), 500


# ================= MATERIAL INSIGHTS ================= #
@analytics_bp.route("/insights/materials", methods=["GET"])
@jwt_required()
def material_insights():
    try:
        user_id = int(get_jwt_identity())
        recs = Recommendation.query.filter_by(user_id=user_id).all()
        
        if not recs:
            return jsonify({"insights": []}), 200
        
        # Group by material
        material_stats = {}
        for rec in recs:
            if not rec.material:
                continue
                
            material_name = rec.material.material_name
            if material_name not in material_stats:
                material_stats[material_name] = {
                    "count": 0,
                    "total_co2": 0,
                    "total_cost": 0,
                    "total_score": 0,
                    "material": rec.material
                }
            
            stats = material_stats[material_name]
            stats["count"] += 1
            stats["total_co2"] += rec.co2_reduction_percent or 0
            stats["total_cost"] += rec.cost_savings_percent or 0
            stats["total_score"] += rec.recommendation_score or 0
        
        # Calculate averages and prepare insights
        insights = []
        for material_name, stats in material_stats.items():
            if stats["count"] > 0:
                insights.append({
                    "material": material_name,
                    "usage_count": stats["count"],
                    "avg_co2_reduction": round(stats["total_co2"] / stats["count"], 1),
                    "avg_cost_savings": round(stats["total_cost"] / stats["count"], 1),
                    "avg_score": round(stats["total_score"] / stats["count"], 3),
                    "recyclability": stats["material"].recyclability_percent,
                    "strength": stats["material"].strength_rating,
                    "cost_per_kg": stats["material"].cost_per_kg,
                    "biodegradability": stats["material"].biodegradability_score
                })
        
        # Sort by average score (highest first)
        insights.sort(key=lambda x: x["avg_score"], reverse=True)
        
        return jsonify({"insights": insights}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get insights: {str(e)}"}), 500