import json

from marshmallow import fields

from applications.extensions import ma


def _json_text_to_obj(value):
    if value in (None, ""):
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


class ProjectMineBindingSchema(ma.Schema):
    id = fields.Integer()
    mine_fid = fields.Integer()
    mine_name_snapshot = fields.Str()
    city_snapshot = fields.Str()
    area_snapshot = fields.Float(allow_none=True)
    status_snapshot = fields.Str(allow_none=True)
    sort_order = fields.Integer()
    create_time = fields.DateTime()
    update_time = fields.DateTime()


class JiangxiMinePlotSchema(ma.Schema):
    id = fields.Integer()
    project_id = fields.Integer()
    mine_fid = fields.Integer()
    subject_code = fields.Str()
    city = fields.Str(allow_none=True)
    county = fields.Str(allow_none=True)
    location_text = fields.Str(allow_none=True)
    plot_code = fields.Str()
    restored_plot_code = fields.Str(allow_none=True)
    plot_category = fields.Str(allow_none=True)
    repair_status = fields.Str(allow_none=True)
    repair_mode = fields.Str(allow_none=True)
    completed_at = fields.Str(allow_none=True)
    area = fields.Float(allow_none=True)
    untreated_area = fields.Float(allow_none=True)
    center_lng = fields.Float(allow_none=True)
    center_lat = fields.Float(allow_none=True)
    closed_year = fields.Str(allow_none=True)
    plot_attr = fields.Str(allow_none=True)
    create_time = fields.DateTime()
    update_time = fields.DateTime()


class ProjectDatasetSchema(ma.Schema):
    id = fields.Integer()
    dataset_kind = fields.Str()
    display_name = fields.Str()
    file_path = fields.Str()
    source_format = fields.Str(allow_none=True)
    mine_fid = fields.Integer(allow_none=True)
    year_start = fields.Integer(allow_none=True)
    year_end = fields.Integer(allow_none=True)
    slice_config_json = fields.Method("get_slice_config")
    create_time = fields.DateTime()
    update_time = fields.DateTime()

    def get_slice_config(self, obj):
        return _json_text_to_obj(obj.slice_config_json)


class ProjectActivityLogSchema(ma.Schema):
    id = fields.Integer()
    event_type = fields.Str()
    actor = fields.Str()
    payload = fields.Method("get_payload")
    create_time = fields.DateTime()

    def get_payload(self, obj):
        return _json_text_to_obj(obj.payload_json)


class ProjectExportRecordSchema(ma.Schema):
    id = fields.Integer()
    format = fields.Str()
    file_path = fields.Str(allow_none=True)
    status = fields.Str()
    request_params = fields.Method("get_request_params")
    create_time = fields.DateTime()
    update_time = fields.DateTime()

    def get_request_params(self, obj):
        return _json_text_to_obj(obj.request_params_json)


class ProjectBackupRecordSchema(ma.Schema):
    id = fields.Integer()
    scope = fields.Str()
    manifest_path = fields.Str()
    status = fields.Str()
    restorable = fields.Boolean()
    create_time = fields.DateTime()
    update_time = fields.DateTime()


class ProjectSummarySchema(ma.Schema):
    id = fields.Integer()
    name = fields.Str()
    region = fields.Str(allow_none=True)
    manager = fields.Str(allow_none=True)
    remark = fields.Str(allow_none=True)
    status = fields.Str()
    monitor_start_year = fields.Integer(allow_none=True)
    monitor_end_year = fields.Integer(allow_none=True)
    mine_count = fields.Integer()
    dataset_count = fields.Integer()
    latest_activity_at = fields.DateTime(allow_none=True)
    create_time = fields.DateTime()
    update_time = fields.DateTime()
