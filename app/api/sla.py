from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.deps import require_permission
from app.services.sla import observed_sla, alert_state
from app.services.incident_automation import reconcile_alerts

router = APIRouter(prefix='/api/system/sla', tags=['SLA & Monitoring'])

@router.get('/current', dependencies=[Depends(require_permission('administration.operations.view'))])
def current(db: Session = Depends(get_db)):
    return observed_sla(db)

@router.get('/alerts', dependencies=[Depends(require_permission('administration.operations.view'))])
def alerts(db: Session = Depends(get_db)):
    return alert_state(db)


@router.post('/reconcile', dependencies=[Depends(require_permission('administration.operations.execute'))])
def reconcile(db: Session = Depends(get_db)):
    return reconcile_alerts(db)
