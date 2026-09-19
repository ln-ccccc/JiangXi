type_map = ["", "变化检测", "目标检测", "地物分类", "场景分类", "影像超分重建", "自动配准", "目标跟踪", "光谱指数计算"]


def str_to_type(strs):
    if strs in type_map:
        return type_map.index(strs)
    return None


def type_to_str(num):
    if num < len(type_map):
        return type_map[num]
    return ""


def items_handle(items):
    for t in items:
        if 'type' in t:
            t['type'] = type_to_str(t['type'])
    # 2026-09-19（S8 测试顺带抓获）：此前只变异不返回，`data = items_handle(data)`
    # 式调用拿到 None，/api/analysis/show 的 data 恒为 null
    return items
