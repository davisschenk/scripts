import argparse
import json
import sys
import time
import fileinput
import traceback

import requests
import string

YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v={youtube_id}'
YOUTUBE_COMMENTS_AJAX_URL = 'https://www.youtube.com/comment_service_ajax'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'

SORT_BY_POPULAR = 0
SORT_BY_RECENT = 1


def find_value(html, key, num_chars=2, separator='"'):
    pos_begin = html.find(key) + len(key) + num_chars
    pos_end = html.find(separator, pos_begin)
    return html[pos_begin: pos_end]


def ajax_request(session, url, params=None, data=None, headers=None, retries=5, sleep=20):
    for _ in range(retries):
        response = session.post(url, params=params, data=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        if response.status_code in [403, 413]:
            return {}
        else:
            time.sleep(sleep)


def download_comments(youtube_id, sort_by=SORT_BY_RECENT, sleep=.1):
    try:
        session = requests.Session()
        session.headers['User-Agent'] = USER_AGENT

        response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))

        if 'uxe=' in response.request.url:
            session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')
            response = session.get(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id))

        html = response.text
        session_token = find_value(html, 'XSRF_TOKEN', 3)
        session_token = session_token.encode('ascii').decode('unicode-escape')

        data = json.loads(find_value(html, 'var ytInitialData = ', 0, '};') + '}')
        ncd = None
        for renderer in search_dict(data, 'itemSectionRenderer'):
            ncd = next(search_dict(renderer, 'nextContinuationData'), None)
            if ncd:
                break

        if not ncd:
            print("Comments disabled", file=sys.stderr)
            # Comments disabled?
            return

        needs_sorting = sort_by != SORT_BY_POPULAR
        continuations = [(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comments')]
        while continuations:
            continuation, itct, action = continuations.pop()
            response = ajax_request(session, YOUTUBE_COMMENTS_AJAX_URL,
                                    params={action: 1,
                                            'pbj': 1,
                                            'ctoken': continuation,
                                            'continuation': continuation,
                                            'itct': itct},
                                    data={'session_token': session_token},
                                    headers={'X-YouTube-Client-Name': '1',
                                             'X-YouTube-Client-Version': '2.20201202.06.01'})

            if not response:
                break
            if list(search_dict(response, 'externalErrorMessage')):
                raise RuntimeError('Error returned from server: ' + next(search_dict(response, 'externalErrorMessage')))

            if needs_sorting:
                sort_menu = next(search_dict(response, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
                if sort_by < len(sort_menu):
                    ncd = sort_menu[sort_by]['continuation']['reloadContinuationData']
                    continuations = [(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comments')]
                    needs_sorting = False
                    continue
                raise RuntimeError('Failed to set sorting')

            if action == 'action_get_comments':
                section = next(search_dict(response, 'itemSectionContinuation'), {})
                for continuation in section.get('continuations', []):
                    ncd = continuation['nextContinuationData']
                    continuations.append((ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comments'))
                for item in section.get('contents', []):
                    continuations.extend([(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comment_replies')
                                          for ncd in search_dict(item, 'nextContinuationData')])

            elif action == 'action_get_comment_replies':
                continuations.extend([(ncd['continuation'], ncd['clickTrackingParams'], 'action_get_comment_replies')
                                      for ncd in search_dict(response, 'nextContinuationData')])

            for comment in search_dict(response, 'commentRenderer'):
                try:
                    yield {'cid': comment['commentId'],
                           'text': ''.join([c['text'] for c in comment['contentText'].get('runs', [])]),
                           'time': comment['publishedTimeText']['runs'][0]['text'],
                           'author': comment.get('authorText', {}).get('simpleText', ''),
                           'channel': comment['authorEndpoint']['browseEndpoint']['browseId'],
                           'votes': comment.get('voteCount', {}).get('simpleText', '0'),
                           'photo': comment['authorThumbnail']['thumbnails'][-1]['url'],
                           'heart': next(search_dict(comment, 'isHearted'), False)}
                except Exception:
                    pass

            time.sleep(sleep)
    except Exception as e:
        print(f"Failed to download comments for {youtube_id} retrying. Error: {e}", file=sys.stderr)
        traceback.print_exc()
        if sleep < 1:
            yield from download_comments(youtube_id, sort_by=sort_by, sleep=sleep*2)


def search_dict(partial, search_key):
    stack = [partial]
    while stack:
        current_item = stack.pop()
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            for value in current_item:
                stack.append(value)


def progressbar(it, prefix="", size=60, file=sys.stdout, count=None):
    count = count or len(it)

    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")
    parser.add_argument("--sort", type=int, default=1, help="How to sort comments 0: Popular, 1: Recent")

    args = parser.parse_args()

    for line in fileinput.input(files=args.files or "-"):
        youtube_id = line.split("=")[-1]

        count = 0
        for comment in download_comments(youtube_id, args.sort):
            comment_text = ''.join(filter(lambda c: c in string.printable, comment["text"])).translate(str.maketrans("\n\r", "  "))
            author_text = ''.join(filter(lambda c: c in string.printable, comment["author"])).translate(str.maketrans("\n\r", "  "))
            print(f"Comment by {author_text}: // \"{comment_text}\" // Url: http://www.youtube.com/channel/{comment['channel']} // Video: {YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)}")

            sys.stderr.write(f"Downloaded {count} comments\r")
            sys.stderr.flush()
            count += 1
        print(f"Downloaded {count} comments from {YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)}", file=sys.stderr)


