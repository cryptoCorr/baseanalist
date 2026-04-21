from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        qs = parse_qs(parsed_path.query)
        
        action = qs.get('action', [''])[0].strip()
        query = qs.get('q', [''])[0].strip()
        
        result_data = {"error": "Geçersiz sorgu veya veri bulunamadı."}
        
        # --- 1. MOD: YENİ ÇIKAN TOKENLARI TARA ---
        if action == "latest":
            try:
                url = "https://api.dexscreener.com/latest/dex/search?q=WETH"
                res = requests.get(url).json()
                
                base_pairs = [p for p in res.get("pairs", []) if p.get("chainId") == "base" and "pairCreatedAt" in p]
                base_pairs.sort(key=lambda x: x.get("pairCreatedAt", 0), reverse=True)
                
                latest_tokens = []
                for p in base_pairs[:8]:
                    latest_tokens.append({
                        "address": p.get("baseToken", {}).get("address", ""),
                        "symbol": p.get("baseToken", {}).get("symbol", ""),
                        "name": p.get("baseToken", {}).get("name", ""),
                        "priceUsd": p.get("priceUsd", "0"),
                        "createdAt": p.get("pairCreatedAt", 0)
                    })
                    
                result_data = {"success": True, "tokens": latest_tokens}
            except Exception as e:
                result_data = {"error": f"DexScreener Hatası: {str(e)}"}

        # --- 2. MOD: SPESİFİK TOKEN ARAMASI ---
        elif query:
            try:
                if query.startswith("0x") and len(query) == 42:
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{query}"
                else:
                    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                    
                res = requests.get(url).json()
                base_pairs = [p for p in res.get("pairs", []) if p.get("chainId") == "base"]
                
                if base_pairs:
                    pair = base_pairs[0]
                    address = pair.get("baseToken", {}).get("address", "").lower()
                    
                    sec_score = "-"
                    try:
                        goplus_url = f"https://api.gopluslabs.io/api/v1/token_security/8453?contract_addresses={address}"
                        gp_res = requests.get(goplus_url).json()
                        if gp_res.get("result") and address in gp_res["result"]:
                            gp_info = gp_res["result"][address]
                            score = 100
                            if gp_info.get("is_honeypot") == "1": score -= 100
                            if gp_info.get("is_open_source") == "0": score -= 20
                            sec_score = max(0, score)
                    except: pass

                    result_data = {
                        "success": True,
                        "address": address,
                        "name": pair.get("baseToken", {}).get("name", ""),
                        "symbol": pair.get("baseToken", {}).get("symbol", ""),
                        "priceUsd": pair.get("priceUsd", "0"),
                        "fdv": pair.get("fdv", 0),
                        "pairAddress": pair.get("pairAddress", ""),
                        "security_score": sec_score
                    }
                else:
                    result_data = {"error": "Base ağında bu token bulunamadı."}
            except Exception as e:
                result_data = {"error": f"API Hatası: {str(e)}"}

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        # Güvenlik duvarlarını esnetiyoruz (CORS)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(result_data).encode('utf-8'))
