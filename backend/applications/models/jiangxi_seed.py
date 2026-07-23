import datetime

from applications.extensions import db


class JiangxiMinePlot(db.Model):
    __tablename__ = "jiangxi_mine_plot"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    mine_fid = db.Column(db.Integer, nullable=False, index=True)
    subject_code = db.Column(db.String(128), nullable=False, index=True)
    city = db.Column(db.String(255))
    county = db.Column(db.String(255))
    location_text = db.Column(db.String(1024))
    plot_code = db.Column(db.String(128), nullable=False, index=True)
    restored_plot_code = db.Column(db.String(128))
    plot_category = db.Column(db.String(255))
    repair_status = db.Column(db.String(255))
    repair_mode = db.Column(db.String(255))
    completed_at = db.Column(db.String(64))
    area = db.Column(db.Float)
    untreated_area = db.Column(db.Float)
    center_lng = db.Column(db.Float)
    center_lat = db.Column(db.Float)
    closed_year = db.Column(db.String(64))
    plot_attr = db.Column(db.String(64))
    create_time = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)
    update_time = db.Column(
        db.DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
        nullable=False,
    )
