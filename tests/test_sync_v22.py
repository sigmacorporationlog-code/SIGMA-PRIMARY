from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.models.sync import SyncDeliveryAck

def test_v22_delivery_ack_model_is_unique_per_device_operation():
    constraints = {c.name for c in SyncDeliveryAck.__table__.constraints}
    assert 'uq_sync_delivery_ack' in constraints
    cols = {c.name for c in SyncDeliveryAck.__table__.columns}
    assert {'school_id','device_id','operation_id','acknowledged_at'} <= cols
