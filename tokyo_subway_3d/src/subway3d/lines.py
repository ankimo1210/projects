"""Which chart on which page describes which line, and the section of it we model.

Chart chainages are read off the printed station labels and then snapped to the
detected station markers (▼); the eye-read value only has to land within ~150 m.
Stations drawn with a red or blue marker are not detected and keep the eye-read
value (that is 大手町 on 丸ノ内線/半蔵門線, 茅場町 on 東西線, 飯田橋 on 有楽町線).
"""
from __future__ import annotations

from dataclasses import dataclass

PAGES = {3: "data/raw/page-03.png", 4: "data/raw/page-04.png", 5: "data/raw/page-05.png"}

# Overpass bbox used for data/raw/osm_*.json (south, west, north, east).
BBOX = (35.640, 139.715, 35.712, 139.795)


@dataclass(frozen=True)
class LineSpec:
    key: str
    name: str  # as printed in the chart title
    osm_name: str  # `name` tag of the OSM ways (substring match)
    page: int
    chart: int  # 0-based index from the top of the page
    dist_right: float  # chainage printed at the right frame edge
    elev_top: float  # T.P. m printed at the top / bottom frame edge
    elev_bottom: float
    stations: tuple[tuple[str, float], ...]  # (name, chart chainage m), chart order

    @property
    def axis(self) -> dict:
        return dict(dist_left=0.0, dist_right=self.dist_right, elev_top=self.elev_top, elev_bottom=self.elev_bottom)


LINES: dict[str, LineSpec] = {
    s.key: s
    for s in [
        # The first ~130 m of the 銀座線 chart is schematic (a 12 m drop), so 青山一丁目 is left out.
        LineSpec("ginza", "銀座線", "東京メトロ銀座線", 3, 0, 12000, 30, -10,
                 (("赤坂見附", 1007), ("溜池山王", 1836), ("虎ノ門", 2602), ("新橋", 3466),
                  ("銀座", 4311), ("京橋", 5018), ("日本橋", 5696), ("三越前", 6245))),
        LineSpec("marunouchi", "丸ノ内線", "東京メトロ丸ノ内線", 3, 1, 7000, 30, -10,
                 (("淡路町", 497), ("大手町", 1370), ("東京", 1952), ("銀座", 3059), ("霞ケ関", 4069),
                  ("国会議事堂前", 4806), ("赤坂見附", 5722))),
        LineSpec("tozai", "東西線", "東京メトロ東西線", 3, 2, 11000, 25, -25,
                 (("飯田橋", 1300), ("九段下", 2028), ("竹橋", 3027), ("大手町", 4070), ("日本橋", 4812),
                  ("茅場町", 5320))),
        LineSpec("hibiya", "日比谷線", "東京メトロ日比谷線", 3, 3, 14000, 20, -20,
                 (("人形町", 5716), ("茅場町", 6604), ("八丁堀", 7103), ("築地", 8029), ("東銀座", 8663),
                  ("銀座", 9098), ("日比谷", 9528), ("霞ケ関", 10635), ("神谷町", 11988), ("六本木", 13518))),
        LineSpec("chiyoda", "千代田線", "東京メトロ千代田線", 4, 0, 16000, 25, -30,
                 (("新御茶ノ水", 9131), ("大手町", 10311), ("二重橋前", 11032), ("日比谷", 11805),
                  ("霞ケ関", 12611), ("国会議事堂前", 13391), ("赤坂", 13981), ("乃木坂", 15181))),
        LineSpec("yurakucho", "有楽町線", "東京メトロ有楽町線", 4, 1, 16000, 30, -35,
                 (("飯田橋", 4250), ("市ケ谷", 5329), ("麹町", 6227), ("永田町", 7099), ("桜田門", 8029),
                  ("有楽町", 9045), ("銀座一丁目", 9494), ("新富町", 10245))),
        LineSpec("hanzomon", "半蔵門線", "東京メトロ半蔵門線", 4, 2, 15000, 30, -35,
                 (("青山一丁目", 247), ("永田町", 1757), ("半蔵門", 2635), ("九段下", 3860), ("神保町", 4367),
                  ("大手町", 6050), ("三越前", 6693))),
        LineSpec("namboku", "南北線", "東京メトロ南北線", 4, 3, 22000, 30, -35,
                 (("麻布十番", 3838), ("六本木一丁目", 5008), ("溜池山王", 5598), ("永田町", 6219),
                  ("四ツ谷", 7711), ("市ケ谷", 8700), ("飯田橋", 9880))),
        LineSpec("mita", "三田線", "都営地下鉄三田線", 5, 2, 10000, 25, -25,
                 (("三田", 250), ("芝公園", 788), ("御成門", 1481), ("内幸町", 2544), ("日比谷", 3471),
                  ("大手町", 4366), ("神保町", 5769), ("水道橋", 6775))),
    ]
}
