// Enhanced Certificate Verification JavaScript
// Add this to static/js/certificate_verification.js or include in template

class CertificateVerifier {
    constructor() {
        this.form = document.getElementById('verifyForm');
        this.submitButton = document.getElementById('verifyButton');
        this.loadingMessage = document.getElementById('loadingMessage');
        this.init();
    }
    
    init() {
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        
        // Generate QR code if certificate data exists
        this.generateQRCode();
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        const certificateNumber = document.getElementById('certificate_number').value.trim();
        if (!certificateNumber) {
            this.showError('Please enter a certificate number');
            return;
        }
        
        this.showLoading();
        
        try {
            const response = await this.verifyCertificate(certificateNumber);
            
            if (response.success) {
                if (response.redirect && response.redirect_url) {
                    // Smooth transition to detailed view
                    this.showSuccess('Certificate found! Redirecting to detailed view...');
                    setTimeout(() => {
                        window.location.href = response.redirect_url;
                    }, 1000);
                } else {
                    // Display inline results
                    this.displayInlineResults(response.certificate);
                }
            } else {
                this.showError(response.error || 'Certificate not found');
            }
        } catch (error) {
            console.error('Verification error:', error);
            this.showError('An error occurred while verifying the certificate. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    async verifyCertificate(certificateNumber) {
        const formData = new FormData();
        formData.append('certificate_number', certificateNumber);
        formData.append('csrfmiddlewaretoken', this.getCSRFToken());
        
        const response = await fetch(window.location.pathname, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    displayInlineResults(certificate) {
        const resultsHTML = this.generateResultsHTML(certificate);
        
        // Create or update results container
        let resultsContainer = document.getElementById('inlineResults');
        if (!resultsContainer) {
            resultsContainer = document.createElement('div');
            resultsContainer.id = 'inlineResults';
            resultsContainer.className = 'mt-8';
            this.form.parentNode.insertBefore(resultsContainer, this.form.nextSibling);
        }
        
        resultsContainer.innerHTML = resultsHTML;
        
        // Smooth scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Generate QR code for the verified certificate
        this.generateQRCodeForCertificate(certificate);
    }
    
    generateResultsHTML(certificate) {
        return `
            <div class="bg-white rounded-lg shadow-sm p-8 max-w-2xl mx-auto">
                <div class="text-center mb-6">
                    <div class="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                        <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                    <h2 class="text-2xl font-bold text-gray-900">Certificate Verified</h2>
                    <p class="mt-2 text-gray-600">This certificate is authentic and valid</p>
                </div>
                
                <div class="border-t border-gray-200 pt-6">
                    <h3 class="text-lg font-semibold text-gray-900 mb-4">Certificate Details</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="text-sm font-medium text-gray-500">Certificate Number</label>
                            <p class="mt-1 text-gray-900 font-mono">${certificate.number}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-500">Type</label>
                            <p class="mt-1 text-gray-900">${certificate.type}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-500">Owner</label>
                            <p class="mt-1 text-gray-900 font-medium">${certificate.owner}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-500">Issue Date</label>
                            <p class="mt-1 text-gray-900">${certificate.issue_date}</p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-500">Status</label>
                            <p class="mt-1">
                                ${certificate.is_valid ? 
                                    '<span class="px-3 py-1 text-sm font-medium rounded-full bg-green-100 text-green-800">Valid</span>' :
                                    '<span class="px-3 py-1 text-sm font-medium rounded-full bg-red-100 text-red-800">' + certificate.status + '</span>'
                                }
                            </p>
                        </div>
                        <div>
                            <label class="text-sm font-medium text-gray-500">Expiry Date</label>
                            <p class="mt-1 text-gray-900">${certificate.expiry_date}</p>
                        </div>
                    </div>
                    
                    ${certificate.property_details ? `
                        <div class="mt-6">
                            <h4 class="text-md font-semibold text-gray-900 mb-3">Property Information</h4>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="text-sm font-medium text-gray-500">Address</label>
                                    <p class="mt-1 text-gray-900">${certificate.property_details.address}</p>
                                </div>
                                <div>
                                    <label class="text-sm font-medium text-gray-500">Size</label>
                                    <p class="mt-1 text-gray-900">${certificate.property_details.size}</p>
                                </div>
                                <div>
                                    <label class="text-sm font-medium text-gray-500">Use Type</label>
                                    <p class="mt-1 text-gray-900">${certificate.property_details.use_type}</p>
                                </div>
                                <div>
                                    <label class="text-sm font-medium text-gray-500">Location</label>
                                    <p class="mt-1 text-gray-900">
                                        ${certificate.property_details.location.district}, 
                                        ${certificate.property_details.location.sector}, 
                                        ${certificate.property_details.location.cell}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    ${certificate.signatures && certificate.signatures.length > 0 ? `
                        <div class="mt-6">
                            <h4 class="text-md font-semibold text-gray-900 mb-3">Digital Signatures</h4>
                            <div class="space-y-3">
                                ${certificate.signatures.map(signature => `
                                    <div class="border border-gray-200 rounded-lg p-3">
                                        <div class="flex justify-between items-start">
                                            <div>
                                                <p class="font-medium text-gray-900">${signature.signer_name}</p>
                                                <p class="text-sm text-gray-500">${signature.role}</p>
                                            </div>
                                            <span class="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                                                Verified
                                            </span>
                                        </div>
                                        <div class="mt-2 text-sm text-gray-600">
                                            <p>Signed: ${signature.signed_at}</p>
                                            <p>Signature ID: 
                                                <span class="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                                    ${signature.signature_id || signature.id}
                                                </span>
                                            </p>
                                            ${signature.document_hash ? `
                                                <p>Hash: 
                                                    <span class="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                                        ${signature.document_hash.substring(0, 20)}...
                                                    </span>
                                                </p>
                                            ` : ''}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="mt-6 flex items-center justify-center">
                        <div class="text-center">
                            <div id="inlineQRCode" class="inline-block p-4 bg-gray-100 rounded-lg mb-2"></div>
                            <p class="text-sm text-gray-600">Scan QR code to verify</p>
                        </div>
                    </div>
                    
                    <div class="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
                        <a href="${certificate.verification_url}" target="_blank"
                           class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-center">
                            View Full Details
                        </a>
                        <button onclick="window.print()" 
                                class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors">
                            Print Certificate
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    generateQRCode() {
        // Generate QR code if on certificate detail page
        if (typeof qrcode !== 'undefined' && document.getElementById('qrcode')) {
            const qr = qrcode(0, 'M');
            qr.addData(window.location.href);
            qr.make();
            document.getElementById('qrcode').innerHTML = qr.createImgTag(4);
        }
    }
    
    generateQRCodeForCertificate(certificate) {
        if (typeof qrcode !== 'undefined' && certificate.verification_url) {
            setTimeout(() => {
                const qrContainer = document.getElementById('inlineQRCode');
                if (qrContainer) {
                    const qr = qrcode(0, 'M');
                    qr.addData(certificate.verification_url);
                    qr.make();
                    qrContainer.innerHTML = qr.createImgTag(3);
                }
            }, 100);
        }
    }
    
    showLoading() {
        if (this.submitButton) {
            this.submitButton.disabled = true;
            this.submitButton.innerHTML = `
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Verifying...
            `;
        }
        
        if (this.loadingMessage) {
            this.loadingMessage.classList.remove('hidden');
        }
    }
    
    hideLoading() {
        if (this.submitButton) {
            this.submitButton.disabled = false;
            this.submitButton.textContent = 'Verify Certificate';
        }
        
        if (this.loadingMessage) {
            this.loadingMessage.classList.add('hidden');
        }
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelectorAll('.verification-notification');
        existing.forEach(el => el.remove());
        
        // Create new notification
        const notification = document.createElement('div');
        notification.className = `verification-notification fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-sm ${
            type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
            type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
            'bg-blue-100 text-blue-800 border border-blue-200'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    ${type === 'success' ? 
                        '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>' :
                        type === 'error' ?
                        '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>' :
                        '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
                    }
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-4 flex-shrink-0">
                    <button class="inline-flex text-gray-400 hover:text-gray-600 focus:outline-none" onclick="this.parentElement.parentElement.parentElement.remove()">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new CertificateVerifier();
});

// Export for manual initialization if needed
window.CertificateVerifier = CertificateVerifier;