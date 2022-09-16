"""prefixes.py - contains only project-specific CURIE prefix maps."""

# Note this is a *reverse* prefix map,
# used to normalize one or more IRI prefixes
# to CURIEs
KGOBO_PREFIXES = {
    "http://biomodels.net/SBO/SBO_":"SBO",
    "http://evs.nci.nih.gov/ftp1/NDF-RT/NDF-RT.owl#":"NDFRT",
    "http://purl.bioontology.org/ontology/MESH/":"MESH",
    "http://purl.obolibrary.org/GO_":"GO",
    "http://purl.obolibrary.org/NCBITaxon_":"NCBITaxon",
    "http://purl.obolibrary.org/obo/GNO_":"GNO",
    "http://www.ncbi.nlm.nih.gov/gene/":"NCBIGENE",
    "https://books.google.com/books?id=":"GOOGLE.BOOKS",
    "https://doi.org/":"DOI",
    "https://viaf.org/":"VIAF",
    "https://www.jstor.org/stable/":"JSTOR",
    "https://www.wikidata.org/wiki/":"WIKIDATA",
    "https://www.worldcat.org/oclc/":"OCLC",
    "obo:bco.owl/BCO_":"BCO",
}
