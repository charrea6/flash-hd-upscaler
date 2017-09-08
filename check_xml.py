from xml.sax import make_parser
from xml.sax.handler import ContentHandler


def test_xml_correctness(filename):
    try:
        parser = make_parser()
        parser.setContentHandler(ContentHandler())
        parser.parse(filename)
        # print "%s is well-formed" % filename
        return True
    except Exception, e:
        print "%s is NOT well-formed! %s" % (filename, e)
        return False
