from django.shortcuts import render, redirect
from django.conf import settings
import textwrap

from er_to_json_converter import convert_xml_to_json
from er_to_json_converter import update_key_in_xml

import lxml.etree as etree
from django.http import HttpResponse
from django.views.generic.base import View


class HomePageView(View):
    # TODO: allow user to edit XML raw file

    @staticmethod
    def dispatch(request, *args, **kwargs):
        response_text = textwrap.dedent('''\
            <html>
            <head>
                <title>CS4221 Demo</title>
            </head>
            <body>
                <h1>Group 6</h1>
                <p>Hello, world!</p>
            </body>
            </html>
        ''')
        return HttpResponse(response_text)


def upload(request):
    """
    Allow user to upload ER object (XML)
    :param request:
    :return:
    """
    if request.method == 'POST' and request.FILES['er_file']:
        er_file = request.FILES['er_file']
        er_tree = etree.parse(er_file)
        file_content = etree.tostring(er_tree, pretty_print=True)

        request.session['xmlContent'] = file_content
        request.session.save()

        print "upload successful >>>"
        return render(request, 'display_uploaded_file.html', {
            'uploaded_file_content': file_content
        })
    return render(request, 'upload.html')


def generate(request):
    """
    User click generate button
    :param request:
    :return:
    """
    if request.method == 'POST' and request.session.get('xmlContent'):
        xml_content = request.session.get('xmlContent')
        return render(request, 'display_uploaded_file.html', {
            'uploaded_file_content': xml_content
        })
    else:
        print "generate failed >>>"
        uploaded_file_error = "Uploaded file is not found."
        return render(request, 'upload.html', {
            uploaded_file_error: uploaded_file_error
        })


def choose_key(request):
    """
    Prompt user to choose primary key
    :param request:
    :return:
    """
    if request.method == 'POST' and request.session.get('xmlContent'):
        xml_content = request.session.get('xmlContent')
        xml_file = etree.fromstring(xml_content)
        return convert_xml_to_json(request, xml_file)

        # return render(request, 'choose_key.html', {
        #     'uploaded_file_content': "test" + etree.tostring(xmlFile, pretty_print = True)
        # })
    else:
        uploaded_file_error = "Uploaded File is not found."
        return render(request, 'upload.html', {
            uploaded_file_error: uploaded_file_error
        })


def selected_key(request):
    """
    Allow user to select primary key
    This method will auto proceed next table after user select a primary key
    :param request:
    :return:
    """
    if request.method == 'POST' and request.session.get('xmlContent'):
        table_name = request.POST.get('tableName', None)
        primary_key_option = request.POST.get('primaryKeyOption', -1)

        if primary_key_option != -1 and table_name is not None:
            xml_content = request.session.get('xmlContent');
            tree = etree.fromstring(xml_content)
            tree = update_key_in_xml(tree, table_name, primary_key_option);

            file_content = etree.tostring(tree, pretty_print=True)

            request.session['xmlContent'] = file_content
            request.session.save()

            return convert_xml_to_json(request, tree)
        else:
            uploaded_file_error = "Uploaded File is not found."
            return render(request, 'upload.html', {
                uploaded_file_error: uploaded_file_error
            })

        # return render(request, 'choose_key.html', {
        #     'uploaded_file_content': "test" + etree.tostring(xmlFile, pretty_print = True)
        # })
    else:
        return render(request, 'upload.html', {
            "error_message": "Unable to update primary key"
        })
