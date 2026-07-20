import json

from lob_reproductions.provenance.sources import verify_sources

if __name__ == "__main__":
    print(json.dumps(verify_sources(), indent=2))
