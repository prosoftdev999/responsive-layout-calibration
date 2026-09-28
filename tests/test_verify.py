import json
from pathlib import Path

ARTIFACT=Path('/app/output/layout_calibration.json')
EXPECTED=json.loads(Path('/tests/expected.json').read_text())
TOKEN_KEYS={
    'standard_breakpoint','wide_breakpoint','compact_pad','standard_pad','wide_pad',
    'content_cap','sidebar_width','card_min','grid_gap','card_inner_pad','char_factor_milli',
}
PRED_KEYS={
    'request_id','content_left_milli','content_width_milli','main_width_milli','sidebar_present',
    'columns','column_width_milli','header_rows','header_height_milli','first_card_height_milli','tallest_card_height_milli',
}


def load_candidate():
    assert ARTIFACT.is_file(), 'missing /app/output/layout_calibration.json'
    x=json.loads(ARTIFACT.read_text())
    assert set(x)=={'base_tokens','layer_order','recovered_values','predictions','history_predictions','flow_predictions'}
    assert isinstance(x['base_tokens'],dict) and set(x['base_tokens'])==TOKEN_KEYS
    assert all(type(v) is int for v in x['base_tokens'].values())
    assert isinstance(x['layer_order'],list) and all(isinstance(v,str) for v in x['layer_order'])
    assert isinstance(x['recovered_values'],dict)
    assert all(isinstance(k,str) and type(v) is int for k,v in x['recovered_values'].items())
    assert isinstance(x['predictions'],list)
    assert isinstance(x['history_predictions'],list)
    assert isinstance(x['flow_predictions'],list)
    return x


def normalize_predictions(rows, id_key='request_id'):
    out={}
    for row in rows:
        expected_keys=PRED_KEYS if id_key=='request_id' else (PRED_KEYS-{'request_id'})|{'query_id'}
        assert isinstance(row,dict) and set(row)==expected_keys
        rid=row[id_key]
        assert isinstance(rid,str) and rid and rid not in out
        assert type(row['sidebar_present']) is bool
        for key,value in row.items():
            if key not in {id_key,'sidebar_present'}:
                assert type(value) is int
        out[rid]=row
    return out


def test_recovered_model_is_exact():
    x=load_candidate()
    assert x['base_tokens']==EXPECTED['base_tokens']
    assert x['layer_order']==EXPECTED['layer_order']
    assert x['recovered_values']==EXPECTED['recovered_values']


def test_render_predictions_are_exact():
    x=load_candidate()
    assert normalize_predictions(x['predictions'])==normalize_predictions(EXPECTED['predictions'])


def test_history_predictions_are_exact():
    x=load_candidate()
    assert normalize_predictions(x['history_predictions'],'query_id')==normalize_predictions(EXPECTED['history_predictions'],'query_id')


def normalize_flows(rows):
    out={}
    for row in rows:
        assert isinstance(row,dict) and set(row)=={'flow_id','root_line_count','probes'}
        fid=row['flow_id']
        assert isinstance(fid,str) and fid and fid not in out
        assert type(row['root_line_count']) is int and row['root_line_count']>=1
        assert isinstance(row['probes'],list)
        probes={}
        for probe in row['probes']:
            assert isinstance(probe,dict) and set(probe)=={'node_id','left_milli','width_milli'}
            nid=probe['node_id']
            assert isinstance(nid,str) and nid and nid not in probes
            assert type(probe['left_milli']) is int
            assert type(probe['width_milli']) is int and probe['width_milli']>=0
            probes[nid]=probe
        out[fid]={'flow_id':fid,'root_line_count':row['root_line_count'],'probes':probes}
    return out


def test_flex_flow_predictions_are_exact():
    x=load_candidate()
    assert normalize_flows(x['flow_predictions'])==normalize_flows(EXPECTED['flow_predictions'])

