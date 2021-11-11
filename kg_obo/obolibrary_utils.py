import urllib
import requests  # type: ignore


def get_url(oid):
    """
    Retrieve what should be a valid URL for a provided OBO ID,
    though don't check that here.
    """
    ourl = f"http://purl.obolibrary.org/obo/{oid}/{oid}.owl"
    try:
        ret = requests.head(ourl, allow_redirects=True)
        if ret.status_code != 200:
            ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
        else:
            i = 0
            for line in urllib.request.urlopen(ourl):
                i = i + 1
                if i > 3:
                    break
                if "ListBucketResult" in line:
                    ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"

    except Exception:
        ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"

    return ourl

def base_url_exists(oid):
    """
    Returns True if a base version of the provided OBO ID
    exists, as this means we likely used it in the past.
    """
    base_ourl = f"http://purl.obolibrary.org/obo/{oid}/{oid}-base.owl"
    base_exists = True
    try:
        ret = requests.head(base_ourl, allow_redirects=True)
        if ret.status_code != 200:
            base_exists = False
        else:
            i = 0
            for line in urllib.request.urlopen(base_ourl):
                i = i + 1
                if i > 3:
                    break
                if "ListBucketResult" in line:
                    base_exists = False
    except Exception as e:
        base_exists = False

    return base_exists
