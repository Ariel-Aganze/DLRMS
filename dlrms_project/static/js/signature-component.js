class SignatureManager {
    constructor() {
        this.signaturePad = null;
        this.modal = null;
        this.callbacks = {};
    }

    init(modalId = 'signatureModal', canvasId = 'signaturePad') {
        this.modal = document.getElementById(modalId);
        const canvas = document.getElementById(canvasId);
        
        if (canvas) {
            this.signaturePad = new SignaturePad(canvas, {
                backgroundColor: 'rgb(255, 255, 255)',
                penColor: 'rgb(0, 0, 0)'
            });
            
            // Resize canvas to fit container
            this.resizeCanvas(canvas);
            window.addEventListener('resize', () => this.resizeCanvas(canvas));
        }
    }

    resizeCanvas(canvas) {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext("2d").scale(ratio, ratio);
        this.signaturePad.clear();
    }

    show(options = {}) {
        if (this.modal) {
            this.modal.classList.remove('hidden');
            if (options.onSign) {
                this.callbacks.onSign = options.onSign;
            }
            if (options.documentId) {
                this.modal.dataset.documentId = options.documentId;
            }
        }
    }

    hide() {
        if (this.modal) {
            this.modal.classList.add('hidden');
            this.clear();
        }
    }

    clear() {
        if (this.signaturePad) {
            this.signaturePad.clear();
        }
    }

    isEmpty() {
        return this.signaturePad ? this.signaturePad.isEmpty() : true;
    }

    getSignatureData() {
        if (!this.signaturePad || this.signaturePad.isEmpty()) {
            return null;
        }
        return {
            dataUrl: this.signaturePad.toDataURL(),
            svg: this.signaturePad.toSVG(),
            timestamp: new Date().toISOString()
        };
    }

    async sign() {
        if (this.isEmpty()) {
            this.showError('Please draw your signature first.');
            return;
        }

        const signatureData = this.getSignatureData();
        const documentId = this.modal.dataset.documentId;

        if (this.callbacks.onSign) {
            try {
                await this.callbacks.onSign(signatureData, documentId);
                this.hide();
            } catch (error) {
                this.showError('Failed to save signature. Please try again.');
            }
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4';
        errorDiv.textContent = message;
        
        const modalContent = this.modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.insertBefore(errorDiv, modalContent.firstChild);
            setTimeout(() => errorDiv.remove(), 3000);
        }
    }

    // Crypto signature methods for advanced signing
    async generateKeyPair() {
        const keyPair = await window.crypto.subtle.generateKey(
            {
                name: "RSASSA-PKCS1-v1_5",
                modulusLength: 2048,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash: "SHA-256",
            },
            true,
            ["sign", "verify"]
        );
        return keyPair;
    }

    async signDocument(documentHash, privateKey) {
        const encoder = new TextEncoder();
        const data = encoder.encode(documentHash);
        
        const signature = await window.crypto.subtle.sign(
            "RSASSA-PKCS1-v1_5",
            privateKey,
            data
        );
        
        return btoa(String.fromCharCode(...new Uint8Array(signature)));
    }

    async verifySignature(documentHash, signature, publicKey) {
        const encoder = new TextEncoder();
        const data = encoder.encode(documentHash);
        const sig = Uint8Array.from(atob(signature), c => c.charCodeAt(0));
        
        const isValid = await window.crypto.subtle.verify(
            "RSASSA-PKCS1-v1_5",
            publicKey,
            sig,
            data
        );
        
        return isValid;
    }
}

// Initialize global signature manager
window.signatureManager = new SignatureManager();