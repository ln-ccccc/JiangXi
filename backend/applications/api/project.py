from flask import Blueprint, request

from applications.auth.guard import login_required
from applications.common.utils.http import fail_api, success_api
from applications.project_hub.service import (
    archive_project,
    create_backup,
    create_dataset,
    create_export,
    create_project,
    get_project_detail,
    get_project_timeline,
    list_backups,
    list_exports,
    list_projects,
    replace_project_mines,
    restore_backup,
    restore_project,
    update_project,
)

project_api = Blueprint("project_api", __name__, url_prefix="/api/projects")


@project_api.get("")
@login_required
def project_list_api():
    filters = {
        "name": request.args.get("name", type=str),
        "region": request.args.get("region", type=str),
        "status": request.args.get("status", type=str),
        "monitor_year": request.args.get("monitor_year", type=int),
    }
    return success_api(data=list_projects(filters))


@project_api.post("")
@login_required
def project_create_api():
    try:
        return success_api(data=create_project(request.json or {}))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.get("/<int:project_id>")
@login_required
def project_detail_api(project_id):
    try:
        return success_api(data=get_project_detail(project_id))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.patch("/<int:project_id>")
@login_required
def project_update_api(project_id):
    try:
        return success_api(data=update_project(project_id, request.json or {}))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.put("/<int:project_id>/mines")
@login_required
def project_replace_mines_api(project_id):
    try:
        return success_api(data=replace_project_mines(project_id, (request.json or {}).get("mines") or []))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.post("/<int:project_id>/datasets")
@login_required
def project_dataset_create_api(project_id):
    try:
        return success_api(data=create_dataset(project_id, request.json or {}))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.get("/<int:project_id>/timeline")
@login_required
def project_timeline_api(project_id):
    try:
        return success_api(data=get_project_timeline(project_id))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.post("/<int:project_id>/archive")
@login_required
def project_archive_api(project_id):
    try:
        return success_api(data=archive_project(project_id))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.post("/<int:project_id>/restore")
@login_required
def project_restore_api(project_id):
    try:
        return success_api(data=restore_project(project_id))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.post("/<int:project_id>/exports")
@login_required
def project_export_create_api(project_id):
    try:
        return success_api(data=create_export(project_id, request.json or {}))
    except ValueError as exc:
        return fail_api(str(exc)), 400
    except Exception as exc:
        return fail_api(str(exc))


@project_api.get("/<int:project_id>/exports")
@login_required
def project_export_list_api(project_id):
    try:
        return success_api(data=list_exports(project_id))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.post("/<int:project_id>/backups")
@login_required
def project_backup_create_api(project_id):
    try:
        return success_api(data=create_backup(project_id, request.json or {}))
    except ValueError as exc:
        return fail_api(str(exc)), 400
    except Exception as exc:
        return fail_api(str(exc))


@project_api.get("/<int:project_id>/backups")
@login_required
def project_backup_list_api(project_id):
    try:
        return success_api(data=list_backups(project_id))
    except Exception as exc:
        return fail_api(str(exc))


@project_api.post("/<int:project_id>/backups/<int:backup_id>/restore")
@login_required
def project_backup_restore_api(project_id, backup_id):
    try:
        return success_api(data=restore_backup(project_id, backup_id))
    except ValueError as exc:
        return fail_api(str(exc)), 400
    except Exception as exc:
        return fail_api(str(exc))
