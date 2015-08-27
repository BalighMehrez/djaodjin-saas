# Copyright (c) 2015, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''Dynamic pages dealing with legal agreements.'''

import urlparse

from django import forms
from django.conf import settings
from django.template import loader
from django.template.base import Context
from django.forms.widgets import CheckboxInput
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DetailView, ListView

from saas.mixins import ProviderMixin
from saas.models import (Agreement, Signature, get_broker)


class AgreementDetailView(DetailView):
    """
    Show a single agreement (or policy) document. The content of the agreement
    is read from saas/agreements/<slug>.md.

    Template:

    To edit the layout of this page, create a local \
    ``saas/legal/agreement.html`` (`example <https://github.com/djaodjin/\
djaodjin-saas/tree/master/saas/templates/saas/legal/agreement.html>`__).

    Template context:
      - ``page`` The content of the agreement formatted as HTML.
      - ``organization`` The provider of the product
      - ``request`` The HTTP request object
    """

    model = Agreement
    slug_url_kwarg = 'agreement'
    template_name = 'saas/legal/agreement.html'

    def get_context_data(self, **kwargs):
        context = super(AgreementDetailView, self).get_context_data(**kwargs)
        context.update({
                'page': _read_agreement_file(context['agreement'].slug)})
        return context


class AgreementListView(ProviderMixin, ListView):
    """
    List all agreements and policies for a provider site. This typically
    include terms of service, security policies, etc.

    Template:

    To edit the layout of this page, create a local ``saas/legal/index.html``
    (`example <https://github.com/djaodjin/djaodjin-saas/tree/master/saas/\
templates/saas/legal/index.html>`__).

    Template context:
      - ``agreement_list`` List of agreements published by the provider
      - ``organization`` The provider of the product
      - ``request`` The HTTP request object
    """

    model = Agreement
    slug_url_kwarg = 'agreement'
    template_name = 'saas/legal/index.html'


class SignatureForm(forms.Form):
    '''Base form to sign legal agreements.'''

    read_terms = forms.fields.BooleanField(
        label='I have read and understand these terms and conditions',
        widget=CheckboxInput)

    def __init__(self, data=None):
        super(SignatureForm, self).__init__(data=data, label_suffix='')


def _read_agreement_file(slug, context=None):
    import markdown
    if not context:
        context = {'organization': get_broker()}
    source, _ = loader.find_template('saas/agreements/legal_%s.md' % slug)
    return markdown.markdown(source.render(Context(context)))


class AgreementSignView(CreateView):
    """
    For a the request user to sign a legal agreement.

    Template:

    To edit the layout of this page, create a local \
    ``saas/legal/sign.html`` (`example <https://github.com/djaodjin/\
djaodjin-saas/tree/master/saas/templates/saas/legal/sign.html>`__).

    Template context:
      - ``page`` The content of the agreement formatted as HTML.
      - ``organization`` The provider of the product
      - ``request`` The HTTP request object
    """

    model = Agreement
    slug_url_kwarg = 'agreement'
    template_name = 'saas/legal/sign.html'
    form_class = SignatureForm
    redirect_field_name = REDIRECT_FIELD_NAME

    def form_valid(self, form):
        if form.cleaned_data['read_terms']:
            Signature.objects.create_signature(
                self.kwargs.get(self.slug_url_kwarg), self.request.user)
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)

    def get_success_url(self):
        # Use default setting if redirect_to is empty
        redirect_to = self.request.REQUEST.get(
            self.redirect_field_name, settings.LOGIN_REDIRECT_URL)
        # Heavier security check -- don't allow redirection to
        # a different host.
        netloc = urlparse.urlparse(redirect_to)[1]
        if netloc and netloc != self.request.get_host():
            redirect_to = settings.LOGIN_REDIRECT_URL
        return redirect_to

    def get_context_data(self, **kwargs):
        context = super(AgreementSignView, self).get_context_data(**kwargs)
        context.update({
                'page': _read_agreement_file(context['agreement'].slug)})
        return context

