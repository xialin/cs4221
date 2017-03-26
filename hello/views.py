from django.shortcuts import render, redirect
from django.conf import settings
import textwrap

import lxml.etree as etree
from django.http import HttpResponse
from django.views.generic.base import View


class HomePageView(View):

    def dispatch(request, *args, **kwargs):
        response_text = textwrap.dedent('''\
            <html>
            <head>
                <title>Greetings to the world</title>
            </head>
            <body>
                <h1>Greetings to the world</h1>
                <p>Hello, world!</p>
            </body>
            </html>
        ''')
        return HttpResponse(response_text)

def upload(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']

        x = etree.parse(myfile)
       

        fileContent = etree.tostring(x, pretty_print = True)
        request.session['xmlContent'] = fileContent;
        request.session.save();
        return render(request, 'display_uploaded_file.html', {
            'uploaded_file_content': fileContent
        })
    return render(request, 'upload.html')

def generate(request):
    if request.method == 'POST' and request.session.get('xmlContent'):
        

        xmlContent = request.session.get('xmlContent');

        #fileContent = etree.tostring(xmlContent, pretty_print = True)
        return render(request, 'display_uploaded_file.html', {
            'uploaded_file_content': xmlContent
        })
    else : 
        uploaded_file_error = "Uploaded File is not found."
        return render(request, 'upload.html', {
            uploaded_file_error: uploaded_file_error
        })

def choosekey(request):
    if request.method == 'POST' and request.session.get('xmlContent'):
        

        xmlContent = request.session.get('xmlContent');

        return render(request, 'choose_key.html', {
            'uploaded_file_content': xmlContent
        })
    else : 
        uploaded_file_error = "Uploaded File is not found."
        return render(request, 'upload.html', {
            uploaded_file_error: uploaded_file_error
        })
