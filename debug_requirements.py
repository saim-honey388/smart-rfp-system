from sqlmodel import Session, select, create_engine
from apps.api.models.entities import RfpModel, ProposalModel
from apps.api.config.settings import settings

engine = create_engine(settings.database_url)

with Session(engine) as session:
    rfps = session.exec(select(RfpModel)).all()
    print(f"Found {len(rfps)} RFPs")
    for r in rfps:
        print(f"RFP: {r.title} (ID: {r.id})")
        print(f"  Requirements: {r.requirements}")
        
        proposals = session.exec(select(ProposalModel).where(ProposalModel.rfp_id == r.id)).all()
        print(f"  Proposals: {len(proposals)}")
        for p in proposals:
            text_len = len(p.extracted_text) if p.extracted_text else 0
            print(f"    Proposal: {p.contractor} - Text Length: {text_len}")
