import argparse
import config
import datetime
import json
import os
import pdb
import re
import requests

headers = {
    "Authorization": "Bearer {}".format(config.BEARER_TOKEN)
}


def get_user_id(user_name):
    """ツイッターのuser_nameに対応したuser_idを取得する

    Args:
        user_name (str): ユーザ名

    Returns:
        str: user_id
    """

    url = "https://api.twitter.com/2/users/by/username/{user_name}".format(
        user_name=user_name)
    resp = requests.get(url, headers=headers)
    if resp.ok:
        data = resp.json()
        return data["data"].get("id")
    else:
        return None


def get_tweets_once(user_id, pagination_token=None, start_time=None):
    """ツイートを一ページ(100件)分取得する

    Args:
        user_id (str): tweet user id
        pagination_token (str, optional): paginationのtoken. Defaults to None.
        start_time (str, optional): 取得開始日. Defaults to None.

    Returns:
        list[dict]: ツイート
        dict: メタデータ
    """
    url = "https://api.twitter.com/2/users/{user_id}/tweets".format(
        user_id=user_id)
    params = {
        "max_results": 100,
        "tweet.fields": "attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,reply_settings,source,text,withheld"
    }
    if not pagination_token is None:
        params["pagination_token"] = pagination_token

    if not start_time is None:
        params["start_time"] = start_time

    resp = requests.get(url, headers=headers, params=params)
    if resp.ok:
        data = resp.json()
        return data["data"], data["meta"]
    else:
        return None


def get_tweets(user_id, max_tweets=None, start_time=None):
    """ツイートを複数ページ分取得する

    Args:
        user_id (str): user id
        max_tweets (int, optional): 最大ツイート数. Defaults to None.
        start_time (str, optional): ツイート取得開始日. Defaults to None.

    Returns:
        list[dict]: ツイート
    """
    tweets_all = []

    # 1ページ目のtweet取得
    tweets, meta = get_tweets_once(user_id, start_time=start_time)
    tweets_all = tweets + tweets_all

    # 2ページ目以降のtweet取得
    while "next_token" in meta and \
            (max_tweets is None or len(tweets_all) < max_tweets):
        next_token = meta["next_token"]
        tweets, meta = get_tweets_once(user_id, pagination_token=next_token)
        tweets_all += tweets

    return tweets_all


def dump_tweets(dname_root, user_name, max_tweets=None):
    """dname_root以下に、[user_name].jsonファイルを作成し、ツイートを保存する

    Args:
        dname_root (str): 保存ディレクトリ名
        user_name (str): ユーザ名
        max_tweets (int, optional): 最大取得ツイート数. Defaults to None.
    """

    if not os.path.exists(dname_root):
        os.makedirs(dname_root)
    
    # user_nameをファイル名とするファイルにツイートを保存する。
    path_fname_json = os.path.join(args.dname_root, args.user_name + ".json")

    # ツイート追加開始時刻の取得
    # 取得済みツイートがある場合は、最新の取得済みツイートのツイート日時を、ツイート追加開始時刻とする。
    tweets = []
    start_time = None
    if os.path.exists(path_fname_json):
        with open(path_fname_json, "r") as f:
            tweets = json.load(f)
            start_time = re.sub(r"\.\d+Z$", "Z", tweets[0]["created_at"])

    # ツイートの取得
    user_id = get_user_id(user_name)
    tweets += get_tweets(user_id, max_tweets=max_tweets, start_time=start_time)

    # 保存
    with open(path_fname_json, "w") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dname_root")
    parser.add_argument("user_name")
    parser.add_argument("-max_tweets", default=None, type=int)
    args = parser.parse_args()

    dump_tweets(args.dname_root, args.user_name, max_tweets=args.max_tweets)
