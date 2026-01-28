/* ===============================
   EcoPackAI – Product Input Page JS
   =============================== */

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!window.EcoPackAI.AuthManager.isAuthenticated()) {
        window.location.href = '/login';
        return;
    }

    // Initialize UI elements
    const form = document.getElementById('productForm');
    const previewCard = document.querySelector('.preview-card');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    // Form inputs
    const inputs = {
        name: document.getElementById('productName'),
        type: document.getElementById('foodType'),
        weight: document.getElementById('productWeight'),
        fragility: document.getElementById('fragilityLevel'),
        tempYes: document.getElementById('tempYes'),
        tempNo: document.getElementById('tempNo')
    };

    // Preview elements
    const preview = {
        name: document.getElementById('previewName'),
        category: document.getElementById('previewCategory'),
        weight: document.getElementById('previewWeight'),
        fragility: document.getElementById('previewFragility'),
        temp: document.getElementById('previewTemp')
    };

    // Value displays
    const valueDisplays = {
        weight: document.getElementById('weightValue'),
        fragility: document.getElementById('fragilityValue')
    };

    // Initialize form values
    function initializeForm() {
        // Set default values
        inputs.weight.value = 0.5;
        inputs.fragility.value = 5;
        inputs.tempNo.checked = true;
        
        // Update displays
        updateWeightDisplay();
        updateFragilityDisplay();
        updatePreview();
    }

    // Event Listeners
    inputs.name.addEventListener('input', updatePreview);
    inputs.type.addEventListener('change', updatePreview);
    inputs.weight.addEventListener('input', updateWeightDisplay);
    inputs.fragility.addEventListener('input', updateFragilityDisplay);
    inputs.tempYes.addEventListener('change', updatePreview);
    inputs.tempNo.addEventListener('change', updatePreview);

    // Update weight display and preview
    function updateWeightDisplay() {
        const value = parseFloat(inputs.weight.value);
        valueDisplays.weight.textContent = `${value.toFixed(2)} kg`;
        updatePreview();
    }

    // Update fragility display and preview
    function updateFragilityDisplay() {
        const value = parseInt(inputs.fragility.value);
        valueDisplays.fragility.textContent = `${value} / 10`;
        updatePreview();
    }

    // Update preview card
    function updatePreview() {
        const productName = inputs.name.value.trim() || 'Enter Product Name';
        const foodType = inputs.type.value || 'Food Type';
        const weight = parseFloat(inputs.weight.value).toFixed(2) + ' kg';
        const fragility = inputs.fragility.value;
        const temperature = inputs.tempYes.checked ? 'Yes' : 'No';
        
        preview.name.textContent = productName;
        preview.category.textContent = foodType;
        preview.weight.textContent = weight;
        preview.fragility.textContent = fragility;
        preview.temp.textContent = temperature;
        
        // Add visual feedback
        previewCard.classList.add('pulse');
        setTimeout(() => previewCard.classList.remove('pulse'), 300);
    }

    // Form validation
    function validateForm() {
        const errors = [];
        
        if (!inputs.name.value.trim()) {
            errors.push('Product name is required');
            inputs.name.classList.add('is-invalid');
        } else {
            inputs.name.classList.remove('is-invalid');
        }
        
        if (!inputs.type.value) {
            errors.push('Please select a food type');
            inputs.type.classList.add('is-invalid');
        } else {
            inputs.type.classList.remove('is-invalid');
        }
        
        const weight = parseFloat(inputs.weight.value);
        if (isNaN(weight) || weight <= 0 || weight > 50) {
            errors.push('Please enter a valid weight (0.01 - 50 kg)');
            inputs.weight.classList.add('is-invalid');
        } else {
            inputs.weight.classList.remove('is-invalid');
        }
        
        const fragility = parseInt(inputs.fragility.value);
        if (isNaN(fragility) || fragility < 1 || fragility > 10) {
            errors.push('Fragility level must be between 1 and 10');
            inputs.fragility.classList.add('is-invalid');
        } else {
            inputs.fragility.classList.remove('is-invalid');
        }
        
        return errors;
    }

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validate form
        const errors = validateForm();
        if (errors.length > 0) {
            EcoPackAI.UIComponents.showError(errors.join('<br>'), '.alert-container');
            return;
        }
        
        // Prepare data
        const formData = {
            product_name: inputs.name.value.trim(),
            food_type: inputs.type.value,
            weight_kg: parseFloat(inputs.weight.value),
            fragility_level: parseInt(inputs.fragility.value),
            temperature_sensitive: inputs.tempYes.checked
        };
        
        // Show loading state
        const originalBtnText = analyzeBtn.innerHTML;
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Analyzing...
        `;
        
        try {
            // Send analysis request
            const result = await EcoPackAI.ProductAnalysisManager.analyze(formData);
            
            // Show success message
            EcoPackAI.UIComponents.showSuccess(
                `Analysis complete! Found ${result.total_materials} materials. Redirecting...`,
                '.alert-container'
            );
            
            // Redirect to recommendations page
            setTimeout(() => {
                window.location.href = '/recommendations';
            }, 1500);
            
        } catch (error) {
            console.error('Analysis error:', error);
            
            // Show error message
            let errorMessage = 'Analysis failed. Please try again.';
            if (error.message.includes('Session expired')) {
                errorMessage = 'Your session has expired. Please log in again.';
                setTimeout(() => window.location.href = '/login', 2000);
            } else if (error.message.includes('Invalid input')) {
                errorMessage = 'Please check your input values and try again.';
            }
            
            EcoPackAI.UIComponents.showError(errorMessage, '.alert-container');
            
            // Reset button
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = originalBtnText;
        }
    });

    // Food type descriptions (tooltips)
    const foodTypeDescriptions = {
        'Dry Food': 'Non-perishable items like grains, cereals, snacks',
        'Fresh Produce': 'Fruits, vegetables, herbs that need ventilation',
        'Frozen Food': 'Items requiring insulation and moisture protection',
        'Liquid Food': 'Beverages, sauces, oils that need leak-proof packaging',
        'Ready-to-Eat': 'Prepared meals needing microwave-safe materials',
        'Bakery Items': 'Bread, pastries needing moisture control'
    };

    // Add descriptions to food type options
    const foodTypeSelect = inputs.type;
    Array.from(foodTypeSelect.options).forEach(option => {
        if (option.value && foodTypeDescriptions[option.value]) {
            option.title = foodTypeDescriptions[option.value];
        }
    });

    // Fragility level descriptions
    const fragilityDescriptions = {
        1: 'Very sturdy (e.g., canned goods)',
        3: 'Moderately sturdy (e.g., boxed cereals)',
        5: 'Average (e.g., packaged snacks)',
        7: 'Fragile (e.g., chips, crackers)',
        10: 'Very fragile (e.g., glass containers, fresh berries)'
    };

    // Update fragility description
    function updateFragilityDescription() {
        const level = parseInt(inputs.fragility.value);
        const description = fragilityDescriptions[level] || 'Select fragility level';
        
        // Find or create description element
        let descElement = document.getElementById('fragilityDescription');
        if (!descElement) {
            descElement = document.createElement('small');
            descElement.id = 'fragilityDescription';
            descElement.className = 'form-text text-muted mt-1';
            inputs.fragility.parentNode.appendChild(descElement);
        }
        
        descElement.textContent = description;
    }

    // Listen to fragility changes
    inputs.fragility.addEventListener('input', updateFragilityDescription);
    
    // Initialize everything
    initializeForm();
    updateFragilityDescription();
    
    // Add some visual effects
    setTimeout(() => {
        document.querySelectorAll('.form-section').forEach((section, index) => {
            section.style.animationDelay = `${index * 0.1}s`;
            section.classList.add('slide-up');
        });
    }, 100);
});

// Global function for temperature toggle animation
window.toggleTemperature = function(value) {
    const yesBtn = document.getElementById('tempYes');
    const noBtn = document.getElementById('tempNo');
    
    if (value === 'true') {
        yesBtn.classList.add('btn-success');
        yesBtn.classList.remove('btn-outline-success');
        noBtn.classList.add('btn-outline-success');
        noBtn.classList.remove('btn-success');
    } else {
        noBtn.classList.add('btn-success');
        noBtn.classList.remove('btn-outline-success');
        yesBtn.classList.add('btn-outline-success');
        yesBtn.classList.remove('btn-success');
    }
};