from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

class DocumentListView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/document_list.html'

class DocumentUploadView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/document_upload.html'

class DocumentDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/document_detail.html'

class DocumentDownloadView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/document_download.html'