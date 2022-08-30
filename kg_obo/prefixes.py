"""prefixes.py - contains only project-specific CURIE prefix maps."""

# Note this is a *reverse* prefix map,
# used to normalize one or more IRI prefixes
# to CURIEs
KGOBO_PREFIXES = {
    "http://purl.bioontology.org/ontology/MESH/":"MESH",
    "https://books.google.com/books?id=":"GOOGLE.BOOKS",
    "https://doi.org/":"DOI",
    "https://viaf.org/":"VIAF",
    "https://www.jstor.org/stable/":"JSTOR",
    "https://www.wikidata.org/wiki/":"WIKIDATA",
    "https://www.worldcat.org/oclc/":"OCLC",
}
