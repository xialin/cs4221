from django.shortcuts import render, redirect
from django.conf import settings
import textwrap

from er_to_json_converter import convert_xml_to_json
from er_to_json_converter import update_primary_key_in_xml, merge_relationship_in_xml

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


def choose_merge(request):
    """
    Prompt user to merge a relationship into another table
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


def proceed_next(request):
    """
    Allow user to select primary key
    This method will auto proceed next table after user select a primary key
    :param request:
    :return:
    """
    if request.method == 'POST' and request.session.get('xmlContent'):
        xml_content = request.session.get('xmlContent')
        tree = etree.fromstring(xml_content)

        table_name = request.POST.get('tableName', None)
        table_primary_key = request.POST.get('primaryKeyOption', -1)

        merge_table = request.POST.get('merge_table', -1)
        merge_from = request.POST.get('merge_from', None)
        merge_to = request.POST.get('merge_to', None)

        if table_primary_key != -1 and table_name is not None:
            """
            update primary keys in xml
            """
            tree = update_primary_key_in_xml(tree, table_name, table_primary_key)
            file_content = etree.tostring(tree, pretty_print=True)

            request.session['xmlContent'] = file_content
            request.session.save()
            return convert_xml_to_json(request, tree)

        elif merge_table != -1 and merge_from is not None and merge_to is not None:
            """
            merge relationship in xml
            """
            tree = merge_relationship_in_xml(tree, merge_table, merge_from, merge_to)
            file_content = etree.tostring(tree, pretty_print=True)

            request.session['xmlContent'] = file_content
            request.session.save()
            return convert_xml_to_json(request, tree)

        else:
            # TODO(UI): add an error page and allow restart
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
