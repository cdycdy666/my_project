from __future__ import annotations

import logging
from typing import Any, Callable

from .config import Config
from .podcast_index import Episode, PodcastIndex, learning_task_for_episode
from .state import get_last_chat_id, load_daily_reco, save_daily_reco

SendFn = Callable[[str, str], None]

DEFAULT_THEME = "Agent 工程"
REPROMPT_EVERY = 3


def format_switch_prompt(theme: str, pushed_count: int, candidates: list[str]) -> str:
    lines = [
        f"「{theme or '当前主题'}」已经陪你推了 {pushed_count} 集。",
        "下一阶段想换个方向吗？最近 RSS 里够料的候选：",
    ]
    if candidates:
        for index, candidate in enumerate(candidates, start=1):
            lines.append(f"{index}) {candidate}")
    else:
        lines.append("（暂时没找到够料的新方向，可以直接说你想聚焦的主题。）")
    lines.append("回复序号 / 直接说你想聚焦的主题 / 回复「继续」留在当前主题。")
    return "\n".join(lines)


def format_episode_push(theme: str, episode: Episode) -> str:
    lines = [
        f"今天这集（主题：{theme}）：",
        episode.title,
        episode.url,
    ]
    if episode.stage:
        lines.append(f"位置：{episode.stage}")
    lines.append(f"听的时候抓：{learning_task_for_episode(episode)}")
    lines.append("听完可以发我：我听完这集了，我的理解是……")
    return "\n".join(lines)


def run_daily_reco(
    config: Config,
    send: SendFn,
    today: str,
    index: PodcastIndex | None = None,
    rotate_count: int | None = None,
) -> dict[str, Any]:
    if not config.daily_reco_enabled:
        return {"status": "disabled"}

    rotate_count = rotate_count or config.daily_theme_rotate_count
    daily = load_daily_reco(config.state_path)

    if daily.get("last_push_date") == today:
        return {"status": "already_pushed_today"}

    chat_id = daily.get("chat_id") or get_last_chat_id(config.state_path)
    if not chat_id:
        logging.warning("daily reco: no chat_id available to push to")
        return {"status": "no_chat_id"}
    daily["chat_id"] = chat_id

    if index is None:
        index = PodcastIndex.load(config.agent_path, config.rl_path, config.rss_path)

    theme = daily.get("current_theme") or DEFAULT_THEME
    if not daily.get("current_theme"):
        daily["theme_started_at"] = today
    daily["current_theme"] = theme
    pushed_episode_ids = [
        item for item in (daily.get("pushed_episode_ids") or []) if isinstance(item, str)
    ]
    pushed_ids = set(pushed_episode_ids)
    episodes = index.episodes_for_theme(theme, exclude_ids=pushed_ids)

    if not episodes:
        candidates = index.candidate_themes(
            recent_window=config.daily_recent_window,
            exclude_theme=theme,
            pushed_ids=pushed_ids,
        )
        send(chat_id, format_switch_prompt(theme, int(daily.get("pushed_count", 0)), candidates))
        daily["pending_theme_switch"] = True
        daily["candidate_themes"] = candidates
        daily["prompts_since_last_reply"] = 0
        daily["last_push_date"] = today
        save_daily_reco(config.state_path, daily)
        return {"status": "theme_exhausted_prompt"}

    episode = episodes[0]
    send(chat_id, format_episode_push(theme, episode))
    if episode.id not in pushed_ids:
        pushed_episode_ids.append(episode.id)
        pushed_ids.add(episode.id)
    daily["pushed_episode_ids"] = pushed_episode_ids[-500:]
    daily["pushed_count"] = int(daily.get("pushed_count", 0)) + 1
    daily["last_push_date"] = today

    status = "pushed"
    if not daily.get("pending_theme_switch") and daily["pushed_count"] >= rotate_count:
        candidates = index.candidate_themes(
            recent_window=config.daily_recent_window,
            exclude_theme=theme,
            pushed_ids=pushed_ids,
        )
        send(chat_id, format_switch_prompt(theme, daily["pushed_count"], candidates))
        daily["pending_theme_switch"] = True
        daily["candidate_themes"] = candidates
        daily["prompts_since_last_reply"] = 0
        status = "pushed_and_prompt"
    elif daily.get("pending_theme_switch"):
        prompts = int(daily.get("prompts_since_last_reply", 0)) + 1
        if prompts >= REPROMPT_EVERY:
            candidates = daily.get("candidate_themes") or index.candidate_themes(
                recent_window=config.daily_recent_window,
                exclude_theme=theme,
                pushed_ids=pushed_ids,
            )
            send(chat_id, format_switch_prompt(theme, daily["pushed_count"], candidates))
            daily["candidate_themes"] = candidates
            prompts = 0
        daily["prompts_since_last_reply"] = prompts
        status = "pushed_pending"

    save_daily_reco(config.state_path, daily)
    return {"status": status, "episode": episode.id, "theme": theme}
