"""Small, cache-first clients for free public genomic knowledge APIs."""
import json
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from database.db import ExternalQueryCacheRepository, KnowledgeSourceRepository


class ExternalSourceError(RuntimeError):
    pass


class JsonHttpClient:
    def __init__(self, opener: Callable = None, timeout: int = 12):
        self.opener = opener or urlopen
        self.timeout = timeout

    def get(self, url: str):
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "DNA-Genome-Intelligence/1.0"})
        try:
            with self.opener(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise ExternalSourceError(f"Public source returned HTTP {error.code}.") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ExternalSourceError("Public source could not be reached or returned invalid JSON.") from error


class CachedPublicSource:
    cache_days = 30

    def _cached(self, source_id: int, key: str, refresh: bool):
        return None if refresh else ExternalQueryCacheRepository.get(source_id, key)

    def _save(self, source_id: int, key: str, payload: Dict):
        expiry = (datetime.now(timezone.utc) + timedelta(days=self.cache_days)).strftime("%Y-%m-%d %H:%M:%S")
        ExternalQueryCacheRepository.save(source_id, key, payload, expiry)
        return {"payload": payload, "fetched_at": datetime.now(timezone.utc).isoformat(), "expires_at": expiry, "cached": False}


class EnsemblClient(CachedPublicSource):
    base_url = "https://rest.ensembl.org"

    def __init__(self, http: JsonHttpClient = None):
        self.http = http or JsonHttpClient()

    @staticmethod
    def _source_id():
        return KnowledgeSourceRepository.upsert(
            "ensembl-rest", "Ensembl REST", "gene_function",
            version_tag="live", source_url="https://rest.ensembl.org", license="CC BY 4.0",
        )

    def gene_functions(self, gene_symbol: str, refresh: bool = False) -> Dict:
        symbol = gene_symbol.upper()
        source_id = self._source_id()
        key = f"gene-functions:{symbol}"
        cached = self._cached(source_id, key, refresh)
        if cached:
            return {**cached, "source": "Ensembl REST", "source_url": self.base_url}

        gene = self.http.get(
            f"{self.base_url}/lookup/symbol/homo_sapiens/{quote(symbol)}?content-type=application/json"
        )
        gene_id = gene.get("id")
        if not gene_id:
            raise ExternalSourceError("Ensembl did not return a stable gene identifier.")
        xrefs = self.http.get(
            f"{self.base_url}/xrefs/id/{quote(gene_id)}?all_levels=1;content-type=application/json"
        )
        functions = []
        seen = set()
        for item in xrefs if isinstance(xrefs, list) else []:
            if "GO" not in (item.get("dbname") or "").upper():
                continue
            term_id = item.get("primary_id") or item.get("display_id")
            term_name = item.get("description") or item.get("display_id") or term_id
            if term_id and term_id not in seen:
                functions.append({"term_id": term_id, "term_name": term_name, "source_db": item.get("dbname")})
                seen.add(term_id)
        payload = {"gene_symbol": symbol, "ensembl_gene_id": gene_id, "functions": functions}
        saved = self._save(source_id, key, payload)
        return {**saved, "source": "Ensembl REST", "source_url": self.base_url}


class GWASCatalogClient(CachedPublicSource):
    base_url = "https://www.ebi.ac.uk/gwas/summary-statistics/api"

    def __init__(self, http: JsonHttpClient = None):
        self.http = http or JsonHttpClient()

    @staticmethod
    def _source_id():
        return KnowledgeSourceRepository.upsert(
            "gwas-catalog-summary-statistics", "GWAS Catalog Summary Statistics", "research_trait",
            version_tag="live", source_url="https://www.ebi.ac.uk/gwas/summary-statistics/docs/",
        )

    def associations(self, rsid: str, refresh: bool = False) -> Dict:
        normalized_rsid = rsid.lower()
        if not normalized_rsid.startswith("rs") or not normalized_rsid[2:].isdigit():
            raise ValueError("A dbSNP rsID such as rs429358 is required.")
        source_id = self._source_id()
        key = f"associations:{normalized_rsid}"
        cached = self._cached(source_id, key, refresh)
        if cached:
            return {**cached, "source": "GWAS Catalog", "source_url": self.base_url}

        response = self.http.get(f"{self.base_url}/associations/{quote(normalized_rsid)}")
        associations = response.get("_embedded", {}).get("associations", response if isinstance(response, list) else [])
        payload = {"rsid": normalized_rsid, "associations": associations}
        saved = self._save(source_id, key, payload)
        return {**saved, "source": "GWAS Catalog", "source_url": self.base_url}
