#!/usr/bin/env python3
"""Inspect 2005 Norrbotten segment ZIP without downloading 866 MB archive.

Only byte-range requests are allowed. No attempt is made to infer physical
units or CRS from file names. Read ZIP inventory, DBF schema, optional .prj.
"""
from __future__ import annotations
import argparse,io,json,re,struct,urllib.request,urllib.error,zipfile
from datetime import datetime,timezone
from pathlib import Path

URL="https://gis.slu.se/data/slu_forest_map/2005/Data/SegmentShape/Norrbotten.zip"
CHUNK=1024*1024
MAX_SIZE=2_000_000_000

def get_range(url,first,last):
    req=urllib.request.Request(url,headers={"Range":f"bytes={first}-{last}",
        "User-Agent":"Lulea-statistik-segment-archive-inspector/1.0"})
    with urllib.request.urlopen(req,timeout=75) as resp:
        if resp.status!=206:
            raise RuntimeError("HTTP range response is not 206; refusing 866MB full download")
        content=resp.headers.get("Content-Range","")
        match=re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",content)
        if not match or int(match[1])!=first or int(match[2])!=last:
            raise RuntimeError("Unexpected or missing Content-Range: "+content)
        total=int(match[3])
        if total<100 or total>MAX_SIZE:
            raise ValueError("Unexpected source ZIP size: "+str(total))
        data=resp.read(last-first+2)
        if len(data)!=last-first+1:
            raise IOError("Incomplete HTTP range response")
        return data,total

class RemoteFile(io.RawIOBase):
    def __init__(self,url):
        self.url=url
        # Avoid blindly downloading a full large archive if remote source cannot range.
        prefix,total=get_range(url,0,0)
        self.length=total
        self.pos=0
        self.blocks={0:prefix}
        self.requests=1
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        pos=offset+(self.pos if whence==1 else self.length if whence==2 else 0)
        if pos<0:raise ValueError("Negative ZIP seek")
        self.pos=pos
        return pos
    def read(self,n=-1):
        if n is None or n<0:n=self.length-self.pos
        n=max(0,min(n,self.length-self.pos))
        result=bytearray()
        while n:
            offset=self.pos//CHUNK*CHUNK
            if offset not in self.blocks:
                if self.requests>=100:raise RuntimeError("Too many range requests")
                tail=min(offset+CHUNK-1,self.length-1)
                data,total=get_range(self.url,offset,tail)
                if total!=self.length:raise ValueError("Source ZIP changed during inspection")
                self.blocks[offset]=data
                self.requests+=1
                if len(self.blocks)>12:
                    self.blocks.pop(next(iter(self.blocks)))
            block=self.blocks[offset]
            rel=self.pos-offset
            take=min(n,len(block)-rel)
            if take<=0:raise IOError("Nonadvancing ZIP file read")
            result.extend(block[rel:rel+take])
            self.pos+=take
            n-=take
        return bytes(result)

def dbf_fields(zf,name):
    # DBF header and schema require only a few KiB of decompressed content.
    with zf.open(name) as file:
        header=file.read(32)
        if len(header)!=32:raise ValueError("Truncated DBF header")
        records=struct.unpack_from("<I",header,4)[0]
        header_len=struct.unpack_from("<H",header,8)[0]
        record_len=struct.unpack_from("<H",header,10)[0]
        if header_len<33 or header_len>65535:raise ValueError("Invalid DBF schema length")
        fields_raw=file.read(header_len-32)
    cols=[]
    for p in range(0,len(fields_raw)-1,32):
        fld=fields_raw[p:p+32]
        if len(fld)<32 or fld[0]==13:break
        cols.append({"name":fld[:11].split(b"\0",1)[0].decode("latin1").strip(),
                     "type":chr(fld[11]),"width":fld[16],"decimals":fld[17]})
    return {"records":records,"record_length":record_len,"fields":cols}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("metadata/knn_2005_norrbotten_segment_inventory.json"))
    args=p.parse_args()
    result={"created_utc":datetime.now(timezone.utc).isoformat(),
        "source_url":URL,"source":"SLU kNN 2005 segmenterat Norrbotten",
        "status":"not_yet_checked","zip_size_bytes":None,
        "inventory":[],"dbf_schemas":[],"prj_files":[],
        "caution":"Segment means, medians and standard deviations are not native 25m pixel biomass. CRS and unit meanings must be verified."}
    try:
        remote=RemoteFile(URL)
        result["zip_size_bytes"]=remote.length
        with zipfile.ZipFile(remote) as z:
            for info in z.infolist():
                if info.flag_bits & 1:
                    raise ValueError("Encrypted ZIP member; cannot inspect")
                result["inventory"].append({"file":info.filename,"size_bytes":info.file_size})
                if info.filename.lower().endswith(".dbf"):
                    result["dbf_schemas"].append({"file":info.filename,
                                                  **dbf_fields(z,info.filename)})
                if info.filename.lower().endswith(".prj"):
                    if info.file_size>16384:raise ValueError("Unusual PRJ file size")
                    result["prj_files"].append({"file":info.filename,
                              "wkt":z.read(info.filename).decode("utf-8","replace")})
        all_fields=[f["name"] for d in result["dbf_schemas"] for f in d["fields"]]
        result["possible_biomass_columns"]=[f for f in all_fields
             if any(t in f.lower() for t in ("bio","bm","biomass"))]
        result["status"]="metadata_inspected"
        result["network_range_requests"]=remote.requests
    except Exception as error:
        result["status"]="source_inspection_failed"
        result["error"]=repr(error)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    if result["status"]!="metadata_inspected":
        raise SystemExit("Source ZIP inspection failed; see JSON diagnostics")
if __name__=="__main__":main()
