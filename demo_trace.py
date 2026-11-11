"""Demo CP7 từ trace đã lưu: không gọi API và không thay đổi kết quả eval."""
import argparse
import json
from pathlib import Path


def show_case(path, case_id):
    report = json.loads(path.read_text(encoding='utf-8'))
    case = next((item for item in report['cases'] if item['id'] == case_id), None)
    if case is None:
        raise ValueError(f'Không có case {case_id} trong {path.name}')
    result, grade = case['result'], case['grade']
    print(f'\n=== {path.name} / {case_id}: replay trace đã lưu ===')
    print('Question:', case['question'])
    print('Status:', result['status'], '| Score:', grade['score'])
    for event in result['trace']:
        step = event.get('step', '-')
        if event['event'] == 'model':
            print(f"Step {step}: model -> {event['finish']}")
        elif event['event'] == 'tool':
            print(f"Step {step}: {event['name']} {json.dumps(event['arguments'], ensure_ascii=False)}")
            observation = event['result']
            fields = ('ok', 'error', 'message', 'provider', 'captured_at', 'overall',
                      'id', 'name', 'status', 'url', 'updates_total')
            print('  Observation:', json.dumps({k: observation[k] for k in fields if k in observation}, ensure_ascii=False))
        else:
            print('Event:', json.dumps(event, ensure_ascii=False))
    print('\nAnswer:\n' + result['answer'])
    print('\nJudge:', grade['reason'])
    print('Mechanical:', json.dumps(grade['mechanical'], ensure_ascii=False))
    print('Lưu ý: completed và điểm judge không chứng minh câu trả lời đúng; cần đối chiếu observation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', default='A8', help='A8: nhiều bước; H7: lỗi và cải tiến; H8: lỗi còn lại')
    parser.add_argument('--report', default='eval_after.json')
    parser.add_argument('--compare', action='store_true', help='Replay cả baseline và report được chọn')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    paths = [root / 'eval_before.json', root / args.report] if args.compare else [root / args.report]
    try:
        for path in paths:
            show_case(path, args.case.upper())
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
