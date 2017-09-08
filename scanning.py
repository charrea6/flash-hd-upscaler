from elements import DOM_DOCUMENT_XML

def is_dom_document(path):
    return path.endswith(DOM_DOCUMENT_XML)

def is_xfl_file(path):
    return 'LIBRARY' in path or DOM_DOCUMENT_XML in path


def is_publish_settings(path):
    return 'PublishSettings.xml' in path
