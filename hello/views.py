from django.shortcuts import render, redirect
from django.conf import settings
import textwrap

from er_to_json_converter import ConvertXmlToJson
from er_to_json_converter import UpdateKeyInXML

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

        xmlFile = etree.fromstring(xmlContent);

        return ConvertXmlToJson(request, xmlFile);


        # return render(request, 'choose_key.html', {
        #     'uploaded_file_content': "test" + etree.tostring(xmlFile, pretty_print = True)
        # })
    else : 
        uploaded_file_error = "Uploaded File is not found."
        return render(request, 'upload.html', {
            uploaded_file_error: uploaded_file_error
        })

def selectedkey(request):
    if request.method == 'POST' and request.session.get('xmlContent'):
        
        primaryKeyOption = request.POST.get('primaryKeyOption', -1)
        tableName = request.POST.get('tableName', None)

        if (primaryKeyOption != -1):
            xmlContent = request.session.get('xmlContent');

            tree = etree.fromstring(xmlContent);

            tree = UpdateKeyInXML(request, tree, tableName, primaryKeyOption);

            fileContent = etree.tostring(tree, pretty_print = True)
            request.session['xmlContent'] = fileContent;
            request.session.save();

            return ConvertXmlToJson(request, tree);

            

             

        else:
            uploaded_file_error = "Uploaded File is not found."
            return render(request, 'upload.html', {
                uploaded_file_error: uploaded_file_error
            })
        




        # return render(request, 'choose_key.html', {
        #     'uploaded_file_content': "test" + etree.tostring(xmlFile, pretty_print = True)
        # })
    else : 
        uploaded_file_error = "Uploaded File is not found."
        return render(request, 'upload.html', {
            uploaded_file_error: uploaded_file_error
        })