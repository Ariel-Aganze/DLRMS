from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class SignatureListView(LoginRequiredMixin, TemplateView):
    template_name = 'signatures/signature_list.html'

class SignDocumentView(LoginRequiredMixin, TemplateView):
    template_name = 'signatures/sign_document.html'

class VerifySignatureView(TemplateView):
    template_name = 'signatures/verify_signature.html'