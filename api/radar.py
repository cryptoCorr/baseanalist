from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Önyüzden gelen 'q' (arama) parametresini yakala
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query).get('q', [''])[0].strip()
        
        result_data = {"error": "Veri bulunamadı veya geçersiz sorgu."}
        
        if query:
            try:
                # 1. DexScreener'dan Base ağı sorgusu
                if query.startswith("0x") and len(query) == 42:
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{query}"
                else:
                    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                    
                res = requests.get(url).json()
                base_pairs = [p for p in res.get("pairs", []) if p.get("chainId") == "base"]
                
                if base_pairs:
                    pair = base_pairs[0]
                    address = pair.get("baseToken", {}).get("address", "").lower()
                    
                    # 2. GoPlus'tan Güvenlik Sorgusu
                    sec_score = "-"
                    sec_data = {}
                    try:
                        goplus_url = f"https://api.gopluslabs.io/api/v1/token_security/8453?contract_addresses={address}"
                        gp_res = requests.get(goplus_url).json()
                        if gp_res.get("result") and address in gp_res["result"]:
                            gp_info = gp_res["result"][address]
                            score = 100
                            if gp_info.get("is_honeypot") == "1": score -= 100
                            if gp_info.get("is_open_source") == "0": score -= 20
                            sec_data = gp_info
                            sec_score = max(0, score)
                    except: pass

                    # Verileri paketle
                    result_data = {
                        "success": True,
                        "address": address,
                        "name": pair.get("baseToken", {}).get("name", ""),
                        "symbol": pair.get("baseToken", {}).get("symbol", ""),
                        "priceUsd": pair.get("priceUsd", "0"),
                        "fdv": pair.get("fdv", 0),
                        "pairAddress": pair.get("pairAddress", ""),
                        "security_score": sec_score,
                        "security_data": sec_data
                    }
            except Exception as e:
                result_data = {"error": str(e)}

        # Sonucu JSON olarak vitrine yolla
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result_data).encode('utf-8'))
