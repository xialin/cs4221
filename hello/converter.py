import json
import xml.etree.ElementTree as ET
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse

"""
converter.py
main class for handling ER to JSON Schema conversion logic
"""

# =================
#  CONSTANTS
# =================

TYPE_STRONG = 'strong'
TYPE_WEAK = 'weak'

# keys used in JSON Schema
TABLE_NAME = 'name'
TABLE_ATTRIBUTES = 'attributes'
TABLE_PRIMARY_KEY = 'primary_key'
TABLE_FOREIGN_KEYS = 'foreign_keys'
TABLE_UNIQUE = 'unique'
TABLE_ENTITY = "entity"
TABLE_REFERENCES = "references"

# keys used in XML objects
XML_OBJ_ENTITY = 'entity'
XML_OBJ_RELATIONSHIP = 'relationship'
XML_KEY = 'key'
XML_ID = 'id'
XML_NAME = 'name'
XML_ATTRIBUTE = 'attribute'
XML_ATTRIBUTE_TYPE = 'type'
XML_ENTITY_ID = 'entity_id'
XML_RELATION_ID = 'relation_id'
XML_MIN = 'min_participation'
XML_MAX = 'max_participation'
XML_KEYS = 'keys'
XML_FOREIGN_KEY = 'foreignKey'
XML_UNIQUE_KEY = 'uniqueKey'
XML_UNIQUE_KEYS = 'uniqueKeys'
XML_ATTRIBUTES = 'attributes'
XML_CHECKED = 'checked'
XML_MERGED = 'merged'


# =================
#  VALIDATION
# =================
def validate_xml(request, tree):
    """
    Before converting to JSON Schema, validate the input XML
    :param request: request sent from UI which contains the XML content
    :param tree: XML parsed as ElementTree
    :return: processed JSON tables if valid, otherwise response with error message
    """
    try:
        xml_content = request.session.get('xmlContent')

        # basic check:
        for child in tree:
            # only entity and relationship object is recognised
            if child.tag != 'entity' and child.tag != 'relationship':
                return render_error_message(request,
                                            'Invalid object type [' + child.tag + ']. This file can only contain '
                                                                                  'entity or relationship object ')

            # each object contains only valid tags ['attribute', 'key', 'uniqueKey', 'foreignKey']
            for element in child:
                if element.tag not in [XML_ATTRIBUTE, XML_KEY, XML_UNIQUE_KEY, XML_FOREIGN_KEY]:
                    return render_error_message(request,
                                                '[' + child.attrib[XML_NAME] + '] has invalid tag ' + element.tag + '!')

        # select primary key
        entities = convert_from_xml_nodes(tree.findall(XML_OBJ_ENTITY))
        relationships = convert_from_xml_nodes(tree.findall(XML_OBJ_RELATIONSHIP))
        for entity in entities.values():
            if len(entity[XML_KEYS]) > 1:
                return prompt_choose_key_option(request, entity[XML_NAME], xml_content,
                                                get_primary_key_display_options(entity, relationships))
            elif len(entity[XML_KEYS]) == 0:
                return render_error_message(request, entity[XML_NAME] + " has no primary key")

        # merge 1-1 table
        for relationship in relationships.values():
            if relationship["checked"] == "1":
                continue  # skip relationship object checked
            for attribute in relationship[XML_ATTRIBUTES].values():
                if XML_MIN in attribute and XML_MAX in attribute \
                        and attribute[XML_MIN] == "1" and attribute[XML_MAX] == "1":
                    merge_from = relationship[XML_NAME]
                    merge_to = entities[attribute[XML_ENTITY_ID]][XML_NAME]
                    return prompt_merge_option(request, merge_to, merge_from)

    except Exception:
        return render_error_message(request, 'Unexpected error occurred!')

    return convert_xml_to_json(request, tree)


# =================
#  CONVERSION
# =================
def convert_xml_to_json(request, tree):
    """
    Main method for converting ER XML to JSON Schema
    :param request: request sent from UI
    :param tree: XML parsed as ElementTree
    :return: processed JSON tables, otherwise error message when data violates the rule
    """
    try:
        # Prep Data
        entities = convert_from_xml_nodes(tree.findall(XML_OBJ_ENTITY))
        entities_list = sort_entities_into_weak_and_strong(entities)
        weak_entities = entities_list[TYPE_WEAK]
        strong_entities = entities_list[TYPE_STRONG]

        relationships = convert_from_xml_nodes(tree.findall(XML_OBJ_RELATIONSHIP))

        # Start Processing
        processed_tables = process_strong_entities(request, strong_entities, {})

        processed_tables = process_weak_entities(request, weak_entities, entities, relationships, processed_tables)
        if isinstance(processed_tables, HttpResponse):
            return processed_tables

        processed_tables = process_relationships(request, relationships, entities, processed_tables)
        if isinstance(processed_tables, HttpResponse):
            return processed_tables

        for table in processed_tables.values():
            table["type"] = "object"
            table.pop(TABLE_NAME)  # Remove the table name we stored for convenience during processing

        output_json = json.dumps(processed_tables, indent=4)
        request.session['output_json'] = output_json
        request.session.save()
    except Exception:
        return render(request, 'upload.html', {
            'uploaded_file_error': "Unexpected error"
        })

    return render(request, 'display_result.html', {
        'output_json': output_json
    })


def convert_from_xml_nodes(nodes):
    """
    Convert XML into internal nodes for easy access
    :param nodes: objects under XML root data
    :return: internal data structure shared by both entity and relationship
    """
    result = {}
    for node in nodes:
        node_id = node.attrib[XML_ID]
        node_name = node.attrib[XML_NAME]
        node_checked = '0'
        node_merged = '0'
        attributes = {}
        keys = []
        unique_keys = []

        for attribute in node.findall(XML_ATTRIBUTE):
            attributes[attribute.attrib[XML_ID]] = attribute.attrib
        for key in node.findall(XML_KEY):
            keys.append(key.text)
        for key in node.findall(XML_UNIQUE_KEY):
            unique_keys.append(key.text)

        if XML_CHECKED in node.attrib.keys():
            node_checked = node.attrib[XML_CHECKED]
        if XML_MERGED in node.attrib.keys():
            node_merged = node.attrib[XML_MERGED]

        result[node_id] = {
            "id": node_id,
            "name": node_name,
            "checked": node_checked,
            "merged": node_merged,
            "attributes": attributes,
            "keys": keys,
            "uniqueKeys": unique_keys
        }
    return result


def sort_entities_into_weak_and_strong(entities):
    """
    Classify entities into weak and strong type
    To be precise, we call en entity weak when it contains relation_id attribute.
    :param entities: entities dict
    :return: a map contains a list of weak entities and a list of strong entities
    """
    result = {TYPE_WEAK: [], TYPE_STRONG: []}
    for entity_id in entities:
        entity = entities[entity_id]
        relation_id = None
        for attribute in entity[XML_ATTRIBUTES].values():
            if XML_RELATION_ID in attribute:
                relation_id = attribute[XML_RELATION_ID]
                print entity[XML_NAME] + ' has relation_id ' + relation_id
                break

        if relation_id is not None:
            print 'weak: ' + entity[XML_NAME]
            result[TYPE_WEAK].append(entity)
        else:
            result[TYPE_STRONG].append(entity)
    return result


# ----------------------------------
#  CONVERSION -> PROCESS ENTITIES
# ----------------------------------
def process_strong_entities(request, strong_entities, processed_tables):
    """
    Process all strong entities
    :param request: HttpRequest
    :param strong_entities: entity list
    :param processed_tables: list of tables already converted to JSON Schema
    :return:
    """
    for strong_entity in strong_entities:
        processed_tables = process_strong_entity(request, strong_entity, processed_tables)
        if isinstance(processed_tables, HttpResponse):
            return processed_tables
    return processed_tables


def process_strong_entity(request, strong_entity, processed_tables):
    """
    Process single strong entity
    :param request:
    :param strong_entity:
    :param processed_tables:
    :return:
    """
    table_name = strong_entity[XML_NAME]

    primary_key_options = get_primary_key_options(strong_entity)
    assert len(primary_key_options) == 1

    processed_table = process_entity_into_table(request, strong_entity, primary_key_options)
    if isinstance(processed_table, HttpResponse):
        return processed_table

    processed_tables[table_name] = processed_table
    return processed_tables


def process_weak_entities(request, weak_entities, entities, relationships, processed_tables):
    """
    Process all weak entities
    :param request: HttpRequest
    :param weak_entities: weak entity list
    :param entities: total entity list
    :param relationships: relationship list
    :param processed_tables: list of tables already converted to JSON Schema
    :return:
    """
    for weak_entity in weak_entities:
        if is_processed(weak_entity, processed_tables):
            continue
        stack = [weak_entity]
        while len(stack) > 0:
            current_entity = stack.pop()

            dependent_entity = get_dependent_entity(current_entity, entities, relationships)
            if is_processed(dependent_entity, processed_tables):
                dependent_entity_table = processed_tables[dependent_entity[TABLE_NAME]]
                processed_tables = process_weak_entity(request, current_entity, dependent_entity_table,
                                                       processed_tables)
            else:
                if dependent_entity in stack:
                    return render_error_message(request, 'Circular reference is detected in uploaded xml!')
                else:
                    stack.append(current_entity)
                    stack.append(dependent_entity)
    return processed_tables


def get_dependent_entity(weak_entity, entities, relationships):
    """
    For an entity with relation_id as attribute, find the other entity in that relationship
    :param weak_entity:
    :param entities:
    :param relationships:
    :return:
    """
    relationship_id = None
    for attribute in weak_entity[XML_ATTRIBUTES].values():
        if XML_RELATION_ID in attribute:
            relationship_id = attribute[XML_RELATION_ID]
            break
    assert relationship_id is not None

    relationship = relationships[relationship_id]

    dependent_entity_id = None
    for attribute in relationship[TABLE_ATTRIBUTES].values():
        if attribute[XML_ENTITY_ID] != weak_entity[XML_ID]:
            dependent_entity_id = attribute[XML_ENTITY_ID]
            break

    assert dependent_entity_id is not None

    dependent_entity = entities[dependent_entity_id]
    assert dependent_entity is not None

    return dependent_entity


def process_weak_entity(request, weak_entity, dependent_entity_table, processed_tables):
    """
    Process single weak entity
    :param request:
    :param weak_entity:
    :param dependent_entity_table:
    :param processed_tables:
    :return:
    """
    table_name = weak_entity[XML_NAME]
    primary_key_options = get_primary_key_options(weak_entity, dependent_entity_table)
    processed_table = process_entity_into_table(request, weak_entity, primary_key_options, dependent_entity_table)
    if isinstance(processed_table, HttpResponse):
        return processed_table

    processed_tables[table_name] = processed_table
    return processed_tables


def process_entity_into_table(request, entity, primary_key_options, dependent_table=None):
    """
    Convert entity data into JSON object
    :param request:
    :param entity:
    :param primary_key_options:
    :param dependent_table:
    :return:
    """
    table_name = entity[XML_NAME]

    primary_key_index = get_primary_key_index(request, primary_key_options, table_name)  # prompt user if necessary
    if isinstance(primary_key_index, HttpResponse):
        return primary_key_index

    primary_key = primary_key_options[primary_key_index]
    assert len(primary_key) > 0

    attribute_list = get_name_attributes(entity)
    foreign_keys = []
    if dependent_table is not None:
        foreign_keys.append(get_foreign_attributes(dependent_table))

    unique = get_unique_key_options(entity, dependent_table)

    # add foreign keys into attributes
    for foreign_key in foreign_keys:
        for fkKey, fkValue in foreign_key[TABLE_REFERENCES].iteritems():
            if fkKey not in attribute_list:
                attribute_list[fkKey] = fkValue

    processed_table = {
        TABLE_NAME: table_name,
        TABLE_ATTRIBUTES: attribute_list,
        TABLE_PRIMARY_KEY: primary_key,
        # TABLE_FOREIGN_KEYS: foreign_keys,
        TABLE_UNIQUE: unique
    }
    return processed_table


# -------------------------------------
#  CONVERSION -> PROCESS RELATIONSHIPS
# -------------------------------------
def process_relationships(request, relationships, entities, processed_tables):
    """
    Process all relationships
    :param request:
    :param relationships:
    :param entities:
    :param processed_tables:
    :return:
    """
    for relationship in relationships.values():
        if is_processed(relationship, processed_tables):
            continue

        if relationship["merged"] == "1":
            print 'skip relationship ' + relationship[XML_NAME]
            continue

        if not is_valid_relationship(relationship, relationships, entities):
            return render(request, 'upload.html', {
                'uploaded_file_error': "Relationship " + relationship[XML_NAME] + 'is invalid! Please make sure it is '
                                                                                  'connecting the correct entity or '
                                                                                  'relationship! '
            })

        stack = [relationship]
        while len(stack) > 0:
            current = stack.pop()

            dependent_relationship = get_dependent_relationship(current, relationships)
            if dependent_relationship is None or is_processed(dependent_relationship, processed_tables):
                processed_tables = process_relationship_into_table(request, current, processed_tables, entities,
                                                                   relationships)
                # return to UI, ask user whether to merge relationship into another table
                if isinstance(processed_tables, HttpResponse):
                    return processed_tables
            else:
                if dependent_relationship in stack:
                    return render(request, 'upload.html', {
                        'uploaded_file_error': "Circular reference is detected in uploaded xml!"
                    })
                else:
                    stack.append(current)
                    stack.append(dependent_relationship)
    return processed_tables


def is_valid_relationship(relationship, relationships, entities):
    """
    Check if a relationship satisfies basic rules: connect two tables and connected tables exist.
    :param relationship:
    :param relationships:
    :param entities:
    :return:
    """
    dependency_count = 0
    for attribute in relationship[XML_ATTRIBUTES].values():
        if XML_RELATION_ID in attribute:
            if attribute[XML_RELATION_ID] not in relationships.keys():
                return False
            dependency_count += 1
        if XML_ENTITY_ID in attribute:
            if attribute[XML_ENTITY_ID] not in entities.keys():
                return False
            dependency_count += 1
    # relationship should connect to only two foreign tables
    return dependency_count == 2


def get_dependent_relationship(relationship, relationships):
    """
    For a relationship with relation_id as attribute, find the other relationship
    :param relationship:
    :param relationships:
    :return:
    """
    for attribute in relationship[XML_ATTRIBUTES].values():
        if XML_RELATION_ID in attribute:
            relationship_id = attribute[XML_RELATION_ID]
            return relationships[relationship_id]
    return None


def process_relationship_into_table(request, relationship, processed_tables, entities, relationships):
    """
    Convert relationship data into JSON object
    :param request:
    :param relationship:
    :param processed_tables:
    :param entities:
    :param relationships:
    :return:
    """
    table_name = relationship[XML_NAME]
    attributes = {}
    primary_key = []
    foreign_keys = []
    unique = []
    for attribute in relationship[XML_ATTRIBUTES].values():
        if XML_ENTITY_ID in attribute:
            entity_table = processed_tables[entities[attribute[XML_ENTITY_ID]][XML_NAME]]
            entity_name = entity_table[TABLE_NAME]

            # if relationship has [1,1] we can consider merge to entity
            # print '------------------------ ' + table_name + ' to ' + entity_name
            if relationship["checked"] != "1" and attribute[XML_MIN] == "1" and attribute[XML_MAX] == "1":
                return prompt_merge_option(request, entity_name, table_name)

            foreign_key = {
                TABLE_ENTITY: entity_name,
                TABLE_REFERENCES: {}
            }
            
            for key in entity_table[TABLE_PRIMARY_KEY]:
                new_key_name = format_foreign_key(entity_table[TABLE_NAME], key)
                primary_key.append(new_key_name)
                foreign_key[TABLE_REFERENCES][new_key_name] = key

                attr_type = attribute[XML_ATTRIBUTE_TYPE] if XML_ATTRIBUTE_TYPE in attribute else "string"
                attributes[new_key_name] = {
                    "type": attr_type,
                    "references": {
                        entity_table[TABLE_NAME]: key
                    }
                }
            foreign_keys.append(foreign_key)

        if XML_RELATION_ID in attribute:
            relationship_table = processed_tables[relationships[attribute[XML_RELATION_ID]][XML_NAME]]
            relationship_name = relationship_table[TABLE_NAME]

            # if relationship has [1,1] we can consider merge to entity
            if relationship["checked"] != "1" and attribute[XML_MIN] == 1 and attribute[XML_MAX] == 1:
                return prompt_merge_option(request, relationship_name, table_name)

            foreign_key = {
                TABLE_ENTITY: relationship_name,
                TABLE_REFERENCES: {}
            }

            for key in relationship_table[TABLE_PRIMARY_KEY]:
                new_key_name = format_foreign_key(relationship_table[TABLE_NAME], key)
                primary_key.append(new_key_name)
                foreign_key[TABLE_REFERENCES][new_key_name] = key

                attr_type = attribute[XML_ATTRIBUTE_TYPE] if XML_ATTRIBUTE_TYPE in attribute else "string"
                attributes[new_key_name] = {
                    "type": attr_type,
                    "references": {
                        relationship_table[TABLE_NAME]: key
                    }
                }
            foreign_keys.append(foreign_key)

        if XML_NAME in attribute:
            attr_type = attribute[XML_ATTRIBUTE_TYPE] if XML_ATTRIBUTE_TYPE in attribute else "string"
            attributes[attribute[XML_NAME]] = {
                "type": attr_type
            }

    processed_table = {
        TABLE_NAME: table_name,
        TABLE_ATTRIBUTES: attributes,
        TABLE_PRIMARY_KEY: primary_key,
        # TABLE_FOREIGN_KEYS: foreign_keys,
        TABLE_UNIQUE: unique
    }
    processed_tables[table_name] = processed_table
    return processed_tables


# ----------------------
#  CONVERSION -> UTILS
# ----------------------
def is_processed(entity, processed_tables):
    return entity[XML_NAME] in processed_tables.keys()


def get_name_attributes(entity):
    """
    properties belong to the entity, not foreign key
    :param entity:
    :return:
    """
    entity_attribute_names = {}
    for attribute in entity[TABLE_ATTRIBUTES].values():
        if XML_NAME in attribute:
            attr_type = attribute[XML_ATTRIBUTE_TYPE] if XML_ATTRIBUTE_TYPE in attribute else "string"
            entity_attribute_names[attribute[XML_NAME]] = {"type": attr_type}
    return entity_attribute_names


def get_foreign_attributes(foreign_table):
    foreign_key = {
        TABLE_ENTITY: foreign_table[TABLE_NAME],
        TABLE_REFERENCES: {}
    }

    attributes_map = foreign_table[XML_ATTRIBUTES]
    for key in foreign_table[TABLE_PRIMARY_KEY]:
        new_key_name = format_foreign_key(foreign_table[TABLE_NAME], key)
        attribute = attributes_map[key]
        attr_type = attribute[XML_ATTRIBUTE_TYPE]
        if not attr_type:
            attr_type = "string"
        foreign_key[TABLE_REFERENCES][new_key_name] = {
            "type": attr_type,
            "references": {
                foreign_table[TABLE_NAME]: key
            }
        }

    return foreign_key


def get_unique_attributes(primary_key, foreign_keys):
    """
    Construct a flat array of attribute names appearing in the primary key options
    """
    unique = []
    for foreign_key in foreign_keys:
        print foreign_key
        for attr in foreign_key[TABLE_REFERENCES]:
            if attr not in primary_key:
                unique.append(attr)
    return unique


def get_unique_key_options(entity, dominant_entity_table=None):
    """
    We use this function for both weak and strong entities. If weak entity, we MUST provide a dominant_entity_table
    """
    print 'get unique key options for ' + entity[XML_NAME]
    attributes = entity[XML_ATTRIBUTES]
    options = []
    for key in entity[XML_UNIQUE_KEYS]:
        option = []
        # print 'key ' + key
        ids = key.split(",")  # [1] or [2, 3]
        for id in ids:
            if "name" in attributes[id]:
                option.append(attributes[id]["name"])
            else:  # if there's no "name" inside the attribute, it MUST have a relation_id
                # assert (dominant_entity_table is not None)
                assert (XML_RELATION_ID in attributes[id])
                dominant_entity_table_name = dominant_entity_table[TABLE_NAME]
                for key in dominant_entity_table[TABLE_PRIMARY_KEY]:
                    option.append(format_foreign_key(dominant_entity_table_name, key))
        options.append(option)
    return options


def get_primary_key_options(entity, dominant_entity_table=None):
    """
    We use this function for both weak and strong entities. If weak entity, we MUST provide a dominant_entity_table
    """
    # print 'get primary key options for ' + entity[XML_NAME]
    attributes = entity[XML_ATTRIBUTES]
    options = []
    for key in entity[XML_KEYS]:
        option = []
        # print 'key ' + key
        ids = key.split(",")  # [1] or [2, 3]
        for id in ids:
            if "name" in attributes[id]:
                option.append(attributes[id]["name"])
            else:  # if there's no "name" inside the attribute, it MUST have a relation_id
                # assert (dominant_entity_table is not None)
                assert (XML_RELATION_ID in attributes[id])
                dominant_entity_table_name = dominant_entity_table[TABLE_NAME]
                for key in dominant_entity_table[TABLE_PRIMARY_KEY]:
                    option.append(format_foreign_key(dominant_entity_table_name, key))
        options.append(option)
    return options


def get_primary_key_index(request, primary_key_options, table_name):
    primary_key_index = 0
    num_options = len(primary_key_options)
    if num_options > 1:
        xml_content = request.session.get('xmlContent')
        options = []
        current_index = 0  # For convenience sake, we just use zero-based indexing here for the options
        for primary_key in primary_key_options:
            options.append(get_primary_key_as_string(primary_key))
            current_index += 1

        return render(request, 'choose_key.html', {
            'table_name': table_name,
            'uploaded_file_content': xml_content,
            'primaryKeyOptions': options
        })

    return primary_key_index


def get_primary_key_as_string(primary_key):  # e.g.[StaffNumber, Office_Name]
    result = "("
    for key in primary_key:
        result += key + ","
    result = result[:-1]  # Remove the extra comma after the last key
    result += ")"
    return result


def format_foreign_key(foreign_table_name, key):
    return foreign_table_name + "_" + key


def get_primary_key_display_options(entity, relationships):
    attributes = entity[XML_ATTRIBUTES]
    options = []
    for key in entity[XML_KEYS]:
        option = []
        ids = key.split(",")  # [1] or [2, 3]
        for key_id in ids:
            if "name" in attributes[key_id]:
                option.append(attributes[key_id][XML_NAME])
            else:  # if there's no "name" inside the attribute, it MUST have a relation_id
                assert (XML_RELATION_ID in attributes[key_id])
                relationship = relationships[attributes[key_id][XML_RELATION_ID]]
                option.append(relationship[XML_NAME])
        options.append(option)
    return options


# =================
#  UI RESPONSE
# =================
def render_error_message(request, msg):
    return render(request, 'upload.html', {
        'uploaded_file_error': msg
    })


def prompt_user_for_input(prompt):
    user_input = raw_input(prompt)
    return user_input


def prompt_choose_key_option(request, table_name, xml_content, options):
    print "prompt_choose_key_option for table " + table_name

    return render(request, 'choose_key.html', {
        'table_name': table_name,
        'uploaded_file_content': xml_content,
        'primaryKeyOptions': options
    })


def prompt_merge_option(request, merge_to, merge_from):
    print "prompt_merge_option from " + merge_from + " to " + merge_to

    xml_content = request.session.get('xmlContent')
    return render(request, 'choose_merge.html', {
        'uploaded_file_content': xml_content,
        'merge_from': merge_from,
        'merge_to': merge_to
    })


def update_primary_key_in_xml(tree, table_name, primary_key_option):
    for node in tree:
        if node.attrib[XML_NAME] != table_name:
            continue
        key_nodes = node.findall("key")

        for i, key_node in enumerate(key_nodes):
            if i != int(primary_key_option):
                key_node.tag = XML_UNIQUE_KEY
    return tree


def merge_relationship_in_xml(tree, merge_table, merge_from, merge_to):
    """
    # add relation attribute into merge_to table, mark as "to_be_merged"
    # delete relationship entry
    """
    if merge_table == "0":
        for node in tree:
            if node.attrib[XML_NAME] == merge_from:
                node.set("checked", "1")
                node.set("merged", "0")
        return tree

    base_node = None
    relation_node = None
    print 'merge_relationship from ' + merge_from + ' to ' + merge_to
    for node in tree:
        if node.attrib[XML_NAME] == merge_from:
            relation_node = node
            relation_node.set("checked", "1")
            relation_node.set("merged", "1")
        if node.attrib[XML_NAME] == merge_to:
            base_node = node

    next_id = 0
    relation_id = relation_node.attrib[XML_ID]
    for attribute in base_node.findall(XML_ATTRIBUTE):
        if XML_RELATION_ID in attribute.attrib and relation_id == attribute.attrib[XML_RELATION_ID]:
            print 'skip adding relation_id'
            return tree  # relation_id already defined
        if attribute.attrib[XML_ID] > next_id:
            next_id = attribute.attrib[XML_ID]

    relation_attribute = ET.SubElement(base_node, XML_ATTRIBUTE)
    relation_attribute.set(XML_ID, str(int(next_id) + 1))
    relation_attribute.set(XML_RELATION_ID, relation_id)

    return tree
