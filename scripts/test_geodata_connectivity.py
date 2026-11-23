#!/usr/bin/env python3
"""Diagnostic only: test DNS, TCP and explicit FTPS AUTH TLS without logging in."""
import ftplib
import json
import socket
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT=Path("metadata/skogsstyrelsen_slu_connectivity.json")

def dns(host):
    try:
        infos=socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)
        return {"status":"ok","addresses":sorted(set(item[4][0] for item in infos))}
    except Exception as ex:
        return {"status":"failed","error":str(ex)}

def tcp(host,port):
    try:
        with socket.create_connection((host,port),timeout=12) as sock:
            return {"status":"ok","peer":str(sock.getpeername())}
    except Exception as ex:
        return {"status":"failed","error":str(ex)}

def explicit_ftps(host):
    ftp=ftplib.FTP_TLS(timeout=15,context=ssl.create_default_context())
    try:
        greeting=ftp.connect(host,21,timeout=15)
        ftp.auth()  # AUTH TLS handshake, before USER/PASS
        return {"status":"ok","greeting":greeting[:160],"tls_version":ftp.sock.version()}
    except Exception as ex:
        return {"status":"failed","error":str(ex)}
    finally:
        try: ftp.close()
        except Exception: pass

def http_head(url):
    req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"Lulea-public-geodata-connectivity-check/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=15) as resp:
            return {"status":"ok","http_status":resp.status,"content_length":resp.headers.get("Content-Length")}
    except urllib.error.HTTPError as ex:
        # An HTTP 403/405 is a live server response rather than a DNS/TCP failure.
        return {"status":"http_error","http_status":ex.code,"error":str(ex)}
    except Exception as ex:
        return {"status":"failed","error":str(ex)}

def main():
    report={"tested_at_utc":datetime.now(timezone.utc).isoformat(),"purpose":"connectivity-only; no data download and no credentials","checks":{}}
    ftp_host="ftpsks.skogsstyrelsen.se"
    slu_host="gis.slu.se"
    report["checks"]["skogsstyrelsen_dns"]=dns(ftp_host)
    report["checks"]["skogsstyrelsen_tcp_21"]=tcp(ftp_host,21)
    report["checks"]["skogsstyrelsen_tcp_990"]=tcp(ftp_host,990)
    if report["checks"]["skogsstyrelsen_tcp_21"]["status"]=="ok":
        report["checks"]["skogsstyrelsen_explicit_ftps_tls"]=explicit_ftps(ftp_host)
    else:
        report["checks"]["skogsstyrelsen_explicit_ftps_tls"]={"status":"not_attempted","reason":"Port 21 not reachable"}
    report["checks"]["slu_dns"]=dns(slu_host)
    report["checks"]["slu_tcp_443"]=tcp(slu_host,443)
    report["checks"]["slu_2010_raster_head"]=http_head("https://gis.slu.se/data/slu_forest_map/2010/Data/Raster/Rt90/BIOMASS_XX_P_10.tif")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    good=[k for k,v in report["checks"].items() if v["status"]=="ok"]
    print("Reachable checks:",", ".join(good) or "none")
    print("NOTE: Job success only means diagnostics completed, not that the remote servers were reachable.")

if __name__=="__main__":
    main()
