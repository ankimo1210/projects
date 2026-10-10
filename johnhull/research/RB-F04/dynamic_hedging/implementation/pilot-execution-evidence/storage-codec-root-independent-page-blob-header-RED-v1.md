# W2 typed-DAG transport：blob NPY header境界の独立RED

2026-10-10。対象 _pilot_transport.py fixed SHA **c2c2e84f68abae13f19b8221da6ca6b95307a9e4a538e7014dfe254f2e675c7e**。作者snapshot/37PASSは不変のbaselineとして保持します。**このpage pre-allocation境界は未承認（P2）。**

_Pages.page はZIP_STORED単一 blob.npy、physical/expanded member sizeをprotocol.read前に制限します。しかし、blob.npy自身のNPY headerで宣言したdtype・shape・data byte数とbody全長の関係は、この時点で未検査です。NPZ194 B / NPY80 Bでも、uint8 shape(1073741824,) を宣言でき、既存protocol readerへ進みます。既存np.loadは宣言countに従って割当ててからbody不足を拒否するため、事前page割当上界を保てません。

以下はcanonical metadata/receiptの各SHAを自己整合させたD2だけのtiny fixtureです。readerはspyで置き換え、**巨大配列のallocationは0**です。page limit256に対しreader1callが到達した事実を保存します。最初の簡略fixture（空metadata/receipt）でも同経路を観測しましたが、判断根拠は下記の自己整合版です。旧物は書換えていません。

```json
{
  "helper_sha256": "c2c2e84f68abae13f19b8221da6ca6b95307a9e4a538e7014dfe254f2e675c7e",
  "self_consistent_physical_receipt": {
    "schema": "rb-f04-array-receipt-v1",
    "metadata_sha256": "3c56c444918c38f938412afa1b58ca28e37687908200dee4bd135e308c2f8f51",
    "arrays_sha256": "43e3b24d64ad72a27ed1f3e8bebda74d38846e6390fb62654f70cb49e8b81156",
    "uncompressed_bytes": 80,
    "artifact_sha256": "9ef76cafe3f275bd552870db8944f13e2a630b5be8e4349045fa2028241b9b59"
  },
  "page_limit": 256,
  "NPZ_physical_bytes": 194,
  "NPY_expanded_bytes": 80,
  "blob_header_declared_nbytes": 1073741824,
  "protocol_reader_calls": 1,
  "outcome": "AssertionError: protocol reader reached before blob.npy header allocation bound",
  "actual_array_allocation": 0,
  "native_financial_source_CAS_Git_changes": 0
}
```

最小修復はzip.open(blob.npy)の小headerをprotocol.read前に解析し、u1・1D・fortran=False、header終端+nbytes==ZIP member file_size、nbytes<=boundを認証することです。malformed version/header、object/別dtype・巨大shapeもこの同一境界で拒否します。内側の業務NPYには既に前検査があり、これは外側page blobの残りです。

root/作者へ原反例と最小範囲を共有済み。W1稼働source・金融生成/RNG/SDE・live/native/CAS/Git・production/source編集は0。実装の他のlogical値/alias/legacy境界はこのREDで否定していません。probe総reader/import費用は未測定、金融費用0、全returned RAM/実容量/速度/金融資格は未承認のままです。
