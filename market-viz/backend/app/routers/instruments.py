from fastapi import APIRouter
from backend.app.deps import load_instruments
from backend.app.models.schemas import Instrument

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("", response_model=list[Instrument])
def list_instruments():
    return [
        Instrument(
            ticker=i["ticker"],
            name=i.get("name", i["ticker"]),
            asset_class=i.get("asset_class", ""),
            market=i.get("market", ""),
            source=i.get("source", ""),
        )
        for i in load_instruments()
    ]
