#!/usr/bin/env python3
"""Build the PJCS2027 practice book from topic-specific source data.

The book is intentionally a workbook: each page has a distinct reader
deliverable, and every fact that depends on a published rule carries an
evidence ID.  The data in this file is the updateable source of the PDF;
the PDF itself is never edited by hand.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Sequence


PAGE_WIDTH = 498.898
PAGE_HEIGHT = 708.661
MARGIN = 42
CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2
BOTTOM = 42


EVIDENCE = [
    ("E-001", "official", "『Pokémon Champions』チャンピオンシップシリーズ「2027シーズン」について", "PJCS2027の対象ルート、ゲーム内の国・地域設定と居住国、日本の各カテゴリ上位120名、複数アカウントのペナルティ、権利獲得アカウント、Mastersは2010年以前、Global Challenge I〜VIとPJCS2027予選の案内。", "https://champions-news.pokemon-home.com/ja/page/833.html"),
    ("E-002", "official", "2027 Global Challenge I announcement", "Registration, M-C, Double Battles, three-match reward condition, and account linkage for CP.", "https://www.pokemon.com/us/news/take-on-the-2027-global-challenge-i"),
    ("E-003", "official", "Pokémon Champions: Assembling your ideal team", "HOME transfer, Roster Ranch, Trial Recruitment, VP/tickets, training limits.", "https://champions.pokemon.com/en-us/pokemon/"),
    ("E-004", "official", "VGC Tournament Handbook, May 21 2026 revision", "Battle team, regulation updates, team list, equipment, connectivity, Double Battles, online competition.", "https://mcdn.pokemon.com/pokemon-prod/raw/upload/v1/live/static-assets/content-assets/cms2/pdf/play-pokemon/rules/play-pokemon-vgc-tournament-handbook-en.pdf"),
    ("E-005", "official", "2027 VGC Global Challenges page", "2027 Global Challenge months, CP table, best-finish limit, and official-pending dates.", "https://championships.pokemon.com/en-us/about/pokemon-vgc-global-challenge-grand-challenge"),
    ("E-006", "secondary", "GameWith: Global Challenge 2027 I", "A Japanese navigation aid; never a substitute for in-game news or official rules.", "https://gamewith.jp/pokemon-champions/575795"),
    ("E-007", "official strategy", "Mega Raichu X team feature", "A published team-building example and Electric Terrain idea; not a promise of current legality.", "https://www.pokemon.com/us/features/pokemon-champions-how-to-build-a-mega-raichu-x-team"),
    ("E-008", "official strategy", "Mega Mawile team feature", "A published team-building example for a slow, pressure-oriented core; verify the active regulation.", "https://www.pokemon.com/us/features/pokemon-champions-how-to-build-a-mega-mawile-team"),
    ("E-009", "official strategy", "Mega Malamar team feature", "A Contrary engine example and methodical positioning lessons; verify the active regulation.", "https://www.pokemon.com/us/features/pokemon-champions-how-to-build-a-mega-malamar-team"),
    ("E-010", "official strategy", "Mega Emboar team feature", "A complete example with Emboar, Primarina, Sinistcha, Weavile, Aerodactyl, and Garchomp.", "https://www.pokemon.com/us/strategy/pokemon-champions-how-to-build-a-mega-emboar-team"),
    ("E-011", "official news", "Pokémon Champions mobile availability", "Mega Raichu X Electric Surge and Mega Raichu Y No Guard announcement.", "https://www.pokemon.com/us/news/pokemon-champions-comes-to-android-and-ios"),
    ("E-012", "official", "Pokémon Championship Series calendar", "The current event calendar; dates and event pages can change.", "https://championships.pokemon.com/en-us/events/"),
    ("E-013", "official", "Pokémon Champions news archive", "The update stream for new regulations, strategies, and event notices.", "https://champions.pokemon.com/en-us/news/"),
]


@dataclass(frozen=True)
class Module:
    title: str
    goal: str
    lens: str
    rows: tuple[tuple[str, str, str], ...]
    case: str
    counter: str
    lab: str
    evidence: str = ""


def M(title: str, goal: str, lens: str, rows: Sequence[tuple[str, str, str]], case: str, counter: str, lab: str, evidence: str = "") -> Module:
    return Module(title, goal, lens, tuple(rows), case, counter, lab, evidence)


MODULES = [
    M("参加ルートを一枚にする", "いま確定している大会情報と、公式発表を待つ情報を分けて、練習を止めない。", "資格の入口", (
        ("確定", "2027年のMastersは2010年以前生まれ", "年齢区分はE-001で再確認する"),
        ("開催月", "Global Challengeは2027年に複数月で予定", "日付・形式はE-005とゲーム内ニュース"),
        ("未発表", "PJCS2027予選の形式・通過人数", "空欄のまま更新欄へ渡す")),
        "Masterで参加する読者は、まず生年区分を確認し、ゲーム内の国・地域設定と居住国が日本であること、権利獲得後に同じアカウントを使うことを確認する。各カテゴリ上位120名、複数アカウントのペナルティ、2027年5月の予選は、公式の対象大会案内として別欄に置く。『参加できる』と『招待条件を満たす』は分ける。［事実:E-001］",
        "大会名だけで、対象地域・年齢・CPの条件まで決まったと解釈するのが典型的な失敗。未発表の予選を確定日程として練習計画に埋め込まず、更新週を予約する。［未発表:E-005］",
        "公式ページを開き、①参加資格、②登録窓口、③ルールセット、④結果確認の4欄を埋める。最後に『次に発表されたら変わる行』を一つ書く。", "E-001,E-005"),
    M("公式情報の鮮度を管理する", "古い記事を練習の根拠にせず、公式発表とゲーム内表示を同じ更新手順で照合する。", "更新の入口", (
        ("日付", "公開日と大会実施日を別に記録", "日付の変化を見落とさない"),
        ("媒体", "Web、ゲーム内ニュース、登録画面", "公式の一次表示を優先"),
        ("差分", "ルール・対象・報酬の変更", "変更箇所だけを台帳へ追加")),
        "公式の日本語シリーズ案内は、Global Challenge I・IIの開催予定、M-Cのダブルバトル、各カテゴリ上位120名、5月のPJCS2027予選を示す。個別の登録方法や報酬は、各告知とゲーム内ニュースで更新する。［事実:E-001,E-002］",
        "GameWithの導線が分かりやすくても、ランキング条件や対象ポケモンを二次記事だけで決めない。記事のリンクを入口にし、最終判断はゲーム内ニュースと公式規則に戻す。［注意:E-006］",
        "同じ大会を公式Web・ゲーム内ニュース・登録画面で見比べ、食い違いを『確認待ち』として記録する。確認できない日は構築を固定せず、情報確認だけで1時間を終えてよい。", "E-002,E-006"),
    M("CPを目的に組み立てる", "大会参加、結果確認、Championship Points獲得の条件を一つの手順にする。", "登録と結果", (
        ("参加", "ゲーム内Online Competitionsから登録", "Battle Teamを登録時に固定"),
        ("CP", "Trainer Central、Play! Pokémon Access、Support ID", "事前リンクを確認"),
        ("結果", "終了後にランキングと報酬を確認", "リンクを報酬付与まで維持")),
        "Global Challenge Iの告知では、CPを得るにはTrainer CentralとPlay! Pokémon Accessのリンク、Pokémon Champions Support IDが必要と説明される。単に対戦したこととCP対象であることを分けてチェックする。［事実:E-002］",
        "登録後にアカウントをつなげれば間に合うと思い込むと、CP対象外になる可能性がある。練習週にリンク状態を確認し、画面を撮る場合は個人情報を公開しない。",
        "登録前チェックを『アカウント』『Support ID』『Battle Team』『終了後の結果確認』の4カードにし、空欄があれば対戦ではなく準備を行う。", "E-002"),
    M("所持状況ではなく役割から始める", "所持ポケモンに依存せず、必要な役割を先に定義し、候補を後から選べるようにする。", "Rosterの扱い", (
        ("入手", "HOME・Roster Ranch・Trial Recruitment", "候補の入手経路を記録"),
        ("試用", "Trial Recruitmentは短期の判断材料", "試用中は訓練条件を確認"),
        ("育成", "VPやTicketで能力・技を調整", "現行仕様をゲーム内で確認")),
        "公式のチーム構築ページは、HOMEからの訪問、Roster Ranch、1日1回のTrial Recruitment、VPやTicket、訓練機能を説明している。だから最初に『このポケモンを持っているから使う』ではなく、『速い支援が必要』から検索する。［事実:E-003］",
        "候補が手元にないことを理由に、役割の検証まで止めるのはもったいない。レンタル・トライアル・仮想盤面で役割を試し、入手判断は後段に置く。",
        "役割カードを6枚作り、各カードに候補を3体ずつ書く。候補が0体のカードだけ、Roster Ranchや公式ニュースを調べる課題にする。", "E-003"),
    M("Battle Teamと試合中の選出を分ける", "6体の登録チームと、4体の選出を混同せず、登録後に変更しない運用を作る。", "登録の固定", (
        ("登録", "大会に使うBattle Teamを指定", "開始から終了まで変更しない"),
        ("選出", "6体から4体を試合ごとに選ぶ", "相手6体を見て決める"),
        ("確認", "Team ID・一覧・技・持ち物", "提出内容とゲーム内を一致")),
        "Tournament Handbookは、競技用Battle Teamを登録し、形式に応じて4〜6体を使うこと、Team Listが意図したチームの基準になることを説明する。6体を作る作業と、4体の選出を練習する作業を別シートにする。［事実:E-004］",
        "対戦直前に『この枠を別の候補へ変えよう』と考えてBattle Teamを編集すると、登録ルールに触れる危険がある。変更は大会前のバージョン更新で止める。",
        "6体の役割表を作成し、次に代表的な相手3タイプへ4体選出を記入する。提出前には技・特性・持ち物・能力値を照合する。", "E-004"),
    M("合法性を最後に祈らない", "レギュレーション、対象ポケモン、技・特性・持ち物を、構築の各段階で確認する。", "合法性ゲート", (
        ("対象", "現行のregulation setと対象リスト", "HOME・ゲーム内表示も見る"),
        ("個体", "通常入手・HOME・公式配布", "出所を記録"),
        ("設定", "技、特性、持ち物、重複", "Team Listと照合")),
        "Handbookは、Champions大会ではChampionsで入手した個体またはHOMEからの個体、現行の対象リストを参照するよう求める。『公式記事に載っていた』だけで大会合法とは言わない。［事実:E-004］",
        "人気のチーム例をそのままコピーし、規則セットが変わっていることに気づかない。例は設計教材、ゲーム内表示は合法性の判定材料、と役割を分ける。",
        "構築表に『出典』『現行規則で確認した日』『未確認欄』を追加する。未確認が残る構築は、オンライン大会用ではなく練習用とラベル付けする。", "E-004,E-013"),
    M("週1時間を実験にする", "週1回しか遊べなくても、理解・試行・記録・次の仮説を一巡させる。", "時間設計", (
        ("理解", "10分で今日の問いを一つに絞る", "検索を広げない"),
        ("試行", "25分で同条件を複数回試す", "結果ではなく判断を残す"),
        ("振り返り", "15分で差分を分類", "次週の変更を1つにする")),
        "たとえば『初手で守るか集中攻撃か』だけを問いにし、同じ相手の並びを3回試す。勝敗を平均するのではなく、速度・対象・交代のどれが判断を変えたかを書く。",
        "1時間でランクを何戦もこなそうとすると、何を学んだかが残らない。対戦できない週は、リプレイ1本と仮想盤面2つでも実験として成立する。",
        "5分の問い、10分の前提、25分の検証、10分の記録、10分の次週設計。終了時に『次に変えるのは1枠か、1選出か、1手順か』を決める。"),
    M("記録を勝率から判断へ変える", "初心者でも、負けを次の練習に変換できる記録形式を持つ。", "ログの粒度", (
        ("盤面", "自分と相手の4体、HP、状態", "見えていた情報だけ"),
        ("判断", "選択肢と選んだ理由", "結果と理由を分離"),
        ("更新", "次に再現する条件", "変更を一つに限定")),
        "『負けたので火力が足りない』ではなく、『相手の守る可能性を見ず、集中攻撃を選んだ』と書く。すると次の実験は技変更ではなく、相手の守る合図を読むドリルになる。",
        "勝率だけを追うと、運・マッチアップ・操作ミスが混ざる。負けた試合にも、正しい情報から正しい分岐を選べたターンがあるので、そこを残す。",
        "1試合につき『見えていた事実3つ』『候補2つ』『分岐を変えた1手』『次の実験1つ』だけを記録する。",),
    M("1ターンを候補の比較にする", "『何となく攻撃』をやめ、情報、相手の応答、自分の残る盤面を比較する。", "判断の単位", (
        ("情報", "相手の特性・持ち物・速度を確度付きで置く", "未知を未知のまま残す"),
        ("候補", "攻撃・守る・交代・支援を並べる", "理想手だけにしない"),
        ("残り", "相手の最善応答後の盤面", "次ターンも評価")),
        "自分がライチュウXとサポート役、相手が高速アタッカー2体なら、攻撃一択にせず、電気技・守る・速度操作への交代を並べる。相手が片方を守っても、次に何が残るかで選ぶ。",
        "『この技なら倒せる』だけで決めると、守る・交代・先制技で返される。KO確率を見積もれない初心者は、まず相手の反応を3つ書けばよい。",
        "一つの盤面を紙に描き、候補A/B/C、相手の返し、2ターン後の自分の残数を表にする。1時間でこの表を3枚作る。"),
    M("KOと交換の価値を読む", "倒すこと、倒されないこと、交代で位置を得ることを同じ資源表で考える。", "交換の評価", (
        ("即時", "このターンに相手を倒す", "返しの対象を残す"),
        ("継続", "次ターンも攻撃権を残す", "HPと支援役を守る"),
        ("位置", "交代で有利な並びを作る", "1体失うより強い場合もある")),
        "相手の片方を倒せるが、次のターンに自分の支援役が集中攻撃される場合、KOが常に最善とは限らない。守る＋隣の相手へ攻撃し、次の選出を有利にする筋も比較する。",
        "残りHPが少ないポケモンを『もう価値がない』と切り捨てるのは危険。相手の技を吸う、守るでターンをずらす、交代先の安全を作る価値がある。",
        "対戦後、各KOを『即時・継続・位置』で採点し、最も低い評価のKOを一つだけ再検討する。"),
    M("速度を数値ではなく分岐で読む", "速度の完全な情報がなくても、順番が逆になったときの安全手を用意する。", "順番の不確実性", (
        ("確定", "速度操作・先制技・明らかな順番", "確定根拠を記録"),
        ("仮説", "同速、努力値、アイテム", "確信度を下げる"),
        ("保険", "守る・交代・優先度", "逆順でも残る手")),
        "Tailwindの有無だけでなく、相手の優先度技や守るを含めて、速い・遅い・同速の3分岐を作る。『先に動くはず』という一つの仮説に全試合を預けない。",
        "同速を自分に都合よく扱うと、重要ターンだけ逆順になる。分からないときは勝ち筋を失わない保険手を置き、ログに『順番の情報が足りなかった』と書く。",
        "同じ盤面を3回、速度操作あり・なし・逆順で再生する。各回で最初に変わる選択と、その選択を変える情報を記録する。"),
    M("先制技と守るの読み合い", "優先度・守る・集中攻撃が重なるとき、相手の守る価値を評価する。", "優先度の罠", (
        ("先制", "HPを削る、支援を止める", "対象の耐久を確認"),
        ("守る", "集中攻撃を空振りにする", "隣の行動も評価"),
        ("待つ", "守る後の位置を取る", "次の速度を残す")),
        "相手の低HPアタッカーに先制技を打つとき、隣が守るを使うと、対象を倒せても自分の支援役の位置を失うことがある。攻撃先を分散し、相手の守るを利用する線も書く。",
        "先制技は必ず安全ではない。Priority防御、威嚇、タイプ無効、相手の交代があるため、技名より『そのターンに必要な結果』から選ぶ。",
        "先制技を使った3試合から、成功・相打ち・裏目を1つずつ選び、相手の守るを仮定した場合の別手を書く。"),
    M("技・特性・持ち物を三層で確認する", "相手の未知情報を、技・特性・持ち物の順に少しずつ狭める。", "情報の順番", (
        ("技", "対象、命中、優先度、追加効果", "今ターンの危険"),
        ("特性", "場に出た瞬間・常時・条件付き", "交換の価値"),
        ("持ち物", "Sash、Berry、強化・回復", "KOラインの不確実性")),
        "Mega Emboarのような積みを狙うアタッカーにProtectがあるか、Sinistchaの回復・redirectがあるかで、同じ『攻撃』でも相手の返しが変わる。公式例は読み方の教材で、採用可能性は現行規則で確認する。［考察:E-010］",
        "種族名だけで技セットを決めつけると、公開情報と実戦の未知を混ぜる。まず『この行動を可能にする最小の技・特性』を置き、残りは仮説にする。",
        "リプレイ1本を止め、相手の行動を技・特性・持ち物のどの情報で説明したかを色分けする。説明できないものは未確認欄へ送る。", "E-010"),
    M("公開情報を安心材料にしすぎない", "Open Team Listで見える情報と、速度・能力値のように見えない情報を分離する。", "公開と未知", (
        ("見える", "種族、技、特性、持ち物など", "相手もこちらを見る"),
        ("見えない", "実数値、速度、選出意図", "分岐として保持"),
        ("更新", "対戦中に判明した情報", "ログを次の選出へ")),
        "Team Listは情報を増やすが、相手の速度や今回の4体の意図までは固定しない。見える技から、相手が隠したい勝ち筋を二つ推測して初手を決める。［事実:E-004］",
        "公開情報を全部覚えてから動こうとすると時間が足りない。今ターンの選択を変える情報だけを拾い、残りは『次の観察点』にする。",
        "公開情報を『技・特性・持ち物』『選出推定』『速度未確定』の3列にし、初手前に各列1行だけ書く。", "E-004"),
    M("勝ち筋を一文にする", "チーム名や使用率ではなく、どの状態を作れば勝てるかを一文で説明する。", "勝ち筋の圧縮", (
        ("起点", "速度・天候・場・位置", "何を作るか"),
        ("主役", "火力、積み、回復、盤面", "いつ出すか"),
        ("終了", "2体の残り方、時間、交換", "何を守るか")),
        "Mega Malamarの公式例は、ContraryとSuperpower、支援・回復・天候対策で時間を使い、じわじわ盤面を取る構想を示す。勝ち筋は『Malamarを強化する』ではなく『強化のターンを支援で買い、回復で維持する』と書く。［考察:E-009］",
        "『強いポケモンを出して勝つ』は勝ち筋ではない。主役が倒れた後の第2線、相手が速度操作を返した時の線まで一文に含める。",
        "自分の4案それぞれについて、起点→主役→終了の3語を埋め、相手の最善対策を一つ書く。", "E-009"),
    M("リプレイを因果で読む", "勝敗の物語ではなく、選択→相手の応答→次の盤面を因果の鎖として読む。", "レビューの方法", (
        ("入力", "その時点で見えていた情報", "後知恵を混ぜない"),
        ("選択", "候補と採用理由", "理由を一行で"),
        ("結果", "盤面の変化", "次の仮説にする")),
        "3ターン目に負けたとしても、1ターン目の相手の守るを見落としたのか、2ターン目の交代で位置を失ったのかで修正は違う。各ターンを『観測・判断・結果』に分ける。",
        "最後のKOだけを直そうとすると、同じ敗因が再発する。最初に勝ち筋が変わったターンを探し、そこだけ別手を試す。",
        "リプレイ1本を3色で注釈する。赤=情報不足、青=判断ミス、緑=構築・選出の問題。最多色を次週の課題にする。"),
    M("メンタルを手順へ落とす", "焦りや連敗を気合いで抑えず、停止・確認・再開の条件に変える。", "試合間の運用", (
        ("停止", "2試合連続で同じ判断を後悔", "次の対戦を始めない"),
        ("確認", "水分、入力、記録、通信", "外部要因を分ける"),
        ("再開", "次の一問が言える", "変更は1つだけ")),
        "週1時間の練習では、試合数よりも次の一問を残せるかを成功基準にする。大会当日は、結果に応じて計画を変えず、登録・対戦・結果確認の手順を守る。",
        "負けた直後にチームを大改造すると、原因が分からないまま検証ができなくなる。停止条件を先に決め、変更は翌週の実験に送る。",
        "自分の『停止サイン』を3つ書き、試合間カードにする。再開の条件は『次の初手の候補を2つ説明できる』にする。"),
    M("盤面を座標化する", "ダブルバトルの4枠を、攻撃対象と交代先の関係が見える図にする。", "盤面の地図", (
        ("自分左", "攻撃・支援の現在位置", "交代後の枠も書く"),
        ("自分右", "集中対象・守るの連携", "隣との依存を確認"),
        ("相手", "脅威と支援の組み合わせ", "単体ではなく対で読む")),
        "相手の高速アタッカーとredirect役が並ぶ場合、アタッカーだけを見てはいけない。攻撃対象、redirect、守る、交代の4本の矢印を盤面に描く。",
        "ポケモンを個別の強さで評価すると、隣の支援による実効火力・耐久を見落とす。『この2体が並ぶ理由』を一文にする。",
        "4枠の図に、今ターンの脅威を赤、次のターンの出口を青で書く。3つの盤面を同じ縮尺で比較する。"),
    M("守る・集中・分散を選ぶ", "相手の守ると隣の価値を読み、攻撃対象を一体に固定しすぎない。", "対象選択", (
        ("集中", "確実なKOへ資源を集める", "守るで空振りになる"),
        ("分散", "2体のHPを同時に削る", "回復・交換を許す"),
        ("守る", "相手の集中を空振りにする", "隣の攻撃権を失う")),
        "相手のSinistchaがredirectと回復を担うなら、主役だけを殴る選択は回復量を上回れないことがある。支援役を圧迫する手と、主役を守る手を同じ表にする。［考察:E-010］",
        "常に集中攻撃をすればよいわけではない。相手の守る・回復・交換で、次の2ターンに残るHPと位置を比較する。",
        "同じ初手から、集中・分散・守るを各1回選び、2ターン後の『相手の行動可能数』と『自分の勝ち筋』を記録する。", "E-010"),
    M("支援役を攻撃役として読む", "Fake Out、redirect、回復、速度操作を、攻撃技と同じ勝ち筋の一部として評価する。", "支援の仕事", (
        ("一手を買う", "行動を止めて積み・攻撃", "一手の価値を明示"),
        ("対象をずらす", "redirectや交代", "無効化との関係"),
        ("維持する", "回復・耐久・再展開", "何ターン維持するか")),
        "公式のMega Emboar例では、SinistchaがRage Powder、Trick Room、回復で主役の積みを支える。支援役は『火力がない』のではなく、主役の成功条件を変えている。［事実:E-010］",
        "支援役を早く倒すことだけを目指すと、主役の攻撃を通すターンを与える。相手の支援が作る時間と、自分が払う攻撃権を比較する。",
        "支援役を1体選び、①止める、②無視する、③先に主役を倒すの3案を、相手の次の1手込みで比較する。", "E-010"),
    M("速度操作を二つ用意する", "Tailwindと低速切り返しのように、速い盤面と遅い盤面の両方に出口を作る。", "速度の二層構造", (
        ("速い", "Tailwind・先制・高い素早さ", "先に4体を動かす"),
        ("遅い", "Trick Room・耐久・後攻", "相手の速さを反転"),
        ("無操作", "操作役が倒れた後", "素の速度も確認")),
        "Mega Emboar公式例は、AerodactylのTailwindとSinistchaのTrick Roomを併記し、中速の主役がどちらの盤面にも寄せられる設計を示す。［事実:E-010］",
        "速度操作を1枚だけにすると、その役が倒れた瞬間に選択肢がなくなる。二つ目の操作か、操作なしで戦う選出を必ず作る。",
        "4案ごとに、速い展開・遅い展開・操作役不在の3つの選出を作り、どのケースで勝ち筋が消えるかを書く。", "E-010"),
    M("範囲技と単体技を使い分ける", "2体への圧力と確実な一体への打点を、守る・redirect・盤面価値で選ぶ。", "打点の分配", (
        ("範囲", "2体のHPを同時に削る", "Wide Guardなどを確認"),
        ("単体", "確実なKOラインを狙う", "redirectを確認"),
        ("非攻撃", "積み・回復・交代", "次のターンの価値")),
        "Rock Slideのような範囲技を選ぶときは、命中・追加効果・相手の防御手も含める。単体技を選ぶときは、倒した後の隣の行動まで書く。",
        "範囲技なら常に得とは限らない。相手が一体を守るなら実質単体になり、隣の高価値対象を残すことがある。",
        "範囲と単体で2ターン先の盤面を比較し、相手の守る・交代・範囲防御を一つずつ反証として加える。"),
    M("交代で価値を失わない", "交代を逃げではなく、攻撃の無効化・速度再設定・主役の再展開として使う。", "位置の資源", (
        ("入る", "耐性・威嚇・支援を作る", "受ける技を限定"),
        ("出る", "集中を外して次に戻る", "戻る条件を決める"),
        ("残す", "倒される前の一手", "交代後の対象を予想")),
        "Mega Raichu XのElectric Terrainを活かしたいなら、場を作る役を雑に失わず、攻撃を受ける枠と戻る枠を設計する。場・速度・HPのどれを交代で守ったか記録する。［考察:E-007,E-011］",
        "交代すれば安全になるとは限らない。交代先が集中される、場の効果が切れる、選出が狭くなる場合は、守るや攻撃の方が価値を持つ。",
        "一つの敗戦から『交代すべきだったターン』を一つ選び、実際に交代した場合の次の相手行動を2つ書く。", "E-007,E-011"),
    M("6体から4体を選ぶ", "登録チームの役割を、相手の6体に対する4体の機能へ変換する。", "選出の手順", (
        ("主役", "勝ち筋を実行する2体", "初手と後発を分ける"),
        ("支援", "速度・守る・redirect・回復", "隣との相性"),
        ("保険", "相手の主な対策への答え", "出さない価値も確認")),
        "4体を『強い順』で選ばず、初手2体・後発2体の役割を先に置く。相手の高速・低速・範囲・積みの4分類に対して、少なくとも一つの出口を残す。",
        "6体全部を試合に入れたい気持ちは、選出の目的をぼやかす。出さない2体も、相手の選出を縛る情報として価値がある。",
        "相手の想定6体を3つ用意し、各々について初手・後発・保険の4体を記入する。選ばなかった2体の役割も一行で説明する。"),
    M("特殊ギミックの予算を決める", "Mega・場・速度操作などの強い要素を、同じターンに重ねるか分散するか判断する。", "ギミックの資源", (
        ("主役", "どのポケモンに最大の資源を渡すか", "毎試合固定しない"),
        ("競合", "場・速度・積みの同時要求", "1ターンで足りるか"),
        ("代替", "ギミックなしの選出", "主役不在でも戦う")),
        "Mega Raichu Xのように場と攻撃を同時に伸ばせる主役でも、場を作るターンに相手が速度操作を返すことがある。ギミックを使う価値と、使わない安全手を比較する。［考察:E-007,E-011］",
        "『せっかくのMegaだから毎回使う』は判断ではない。相手の守る・交代・場の上書きで、資源を使った後に何が残るかを見る。",
        "各案に『使う条件』『温存する条件』『主役を失った後の代替』を書き、対戦前に一枚で確認できるようにする。", "E-007,E-011"),
    M("終盤の勝ち筋を守る", "残り2体・時間・HP・場の状態を見て、攻撃より安全な選択を選ぶ。", "終盤管理", (
        ("HP", "確定KO・回復・相打ち", "残り回数を数える"),
        ("時間", "制限・試合間・判断時間", "急がない手順"),
        ("場", "速度・天候・地形・状態", "切れるタイミング")),
        "終盤に1体を倒せる場面でも、相手の後発が確定で出てくるなら、守る＋支援で相手の選択肢を減らす方がよい。勝ち筋を『最後に何が残るか』で表す。",
        "序盤のリードを守ろうとして、終盤に守る回数・交代先・回復を失う。残り2体の役割を先に確認し、今ターンの交換を評価する。",
        "リプレイ終盤を一度だけ巻き戻し、攻撃・守る・交代の3案を比較する。勝ち筋が残る手を選び、次のチェックリストにする。"),
    M("仮想盤面を具体的に再生する", "種族名・技・特性・持ち物を含む具体的な盤面で、1ターンの選択を再現する。", "ケース演習", (
        ("自分", "Mega Emboar＋Sinistcha", "積みと回復"),
        ("相手", "Mega Charizard Y＋Whimsicott", "高速・天候・圧力"),
        ("問い", "Bulk Up、Rage Powder、交代", "2ターンの出口")),
        "公式のMega Emboar例にあるEmboar、Primarina、Sinistcha、Weavile、Aerodactyl、Garchompを教材にし、現在の規則セットでの合法性は別に確認する。初手Emboar＋Sinistchaなら、積み・redirect・Trick Roomのどれを優先するかを比較する。［事実:E-010］",
        "公式記事の技・努力値・持ち物を、そのまま2027年のオンライン大会へ持ち込めるとは限らない。教材の事実と大会の合法性判定を別の欄に置く。［注意:E-004,E-010］",
        "ケースを3回再生する。①相手が攻撃、②相手が守る、③相手が速度操作。各回で『次に守るポケモン』と『捨てる情報』を決める。", "E-004,E-010"),
    M("初手圧力案を調整する", "Mega Raichu Xのような速い主役を、場・支援・後発の3方向から調整する。", "プランA", (
        ("主役", "Mega Raichu X候補", "Electric Terrainと物理圧力の確認"),
        ("支援", "Fake Out・速度・回復候補", "主役の1ターンを買う"),
        ("後発", "場が消えても戦う枠", "主役不在の出口")),
        "公式のMega Raichu X記事は、Electric Terrainを活かし、相手の主要な火力を先に止める考え方を示す。初心者は種族の採用より、①場を作る、②先に動く、③場なしでも一手を残す、をテストする。［考察:E-007,E-011］",
        "先手を取れると決めつけて、相手のProtect・優先度・速度操作を無視しない。速い案ほど、逆順になった時の守る・交代が必要になる。",
        "主役・場・速度・支援・対面打点・後発の6枠に候補を2つずつ入れ、各候補が『何を解決し、何を悪化させるか』を一行で書く。", "E-007,E-011"),
    M("低速切り返し案を調整する", "Mega MawileやMega Emboarのような中低速主役を、支援と速度反転で通す。", "プランB", (
        ("主役", "Mega Mawile／Mega Emboar候補", "積み・打点・耐久"),
        ("操作", "Trick Room・redirect", "起動役を守る"),
        ("速い出口", "Fake Out・Tailwind・後発", "操作が切れた後")),
        "Mega Emboar公式例は、Bulk Up、PrimarinaのCalm Mind、SinistchaのRage Powder／Trick Roomを役割の連鎖として示す。低速案は『Trick Roomを貼る』で終わらず、貼った後の2ターンの攻撃計画まで作る。［事実:E-010］",
        "低速だからといって、毎回Trick Roomを初手で狙うと、相手の挑発・集中攻撃・交代で崩れる。起動しない選出と、1ターン待つ選択を用意する。［注意:E-010］",
        "起動成功・起動失敗・相手が遅い、の3ケースで、主役が攻撃する順番と支援役が残す行動を記入する。", "E-008,E-010"),
    M("条件操作案を調整する", "Mega Malamarのように、場や能力変化を積み重ねて勝つ案のリスクを管理する。", "プランC", (
        ("条件", "Contrary・Superpower・天候", "何が起点か"),
        ("維持", "回復・pivot・速度", "主役を早く失わない"),
        ("崩壊", "挑発・クリティカル・強制交代", "代替勝ち筋")),
        "公式のMega Malamar例は、Contraryで自己強化し、回復・pivot・天候対策を組み合わせる長期戦の考え方を示す。条件操作案は、強化量ではなく『何ターン維持できるか』を測る。［事実:E-009］",
        "積みを急ぐと、相手の集中攻撃で主役を失う。最初のターンを回復・交代・相手の支援阻止に使う価値を比較する。",
        "強化が1回・2回・0回の3状態で、相手の最善対策と自分の残り役割を表にする。積み回数より、次に確定する選択を評価する。", "E-009"),
    M("バランス案を主軸差し替えする", "Mega Raichu X・Mega Mawile・Mega Malamar・Mega Emboarなど、主役を差し替えても役割表を壊さない。", "プランD", (
        ("主軸", "火力・耐久・場のどれを担うか", "主軸候補を比較"),
        ("共通枠", "速度・支援・保険", "主軸を替えても残す"),
        ("差替枠", "相手への回答", "新しい弱点を検証")),
        "公式戦略記事にはMega Raichu X、Mega Mawile、Mega Malamar、Mega Emboarの構築例がある。主役の知名度ではなく、既存の速度・支援・対面回答が差し替えでどう変わるかを測る。［事実:E-007〜E-010］",
        "主軸だけを入れ替え、他の5体をそのままにすると、タイプ・速度・支援の目的がずれる。差し替え後に役割表と初手2組を作り直す。",
        "4案を同じ6軸で採点し、主軸変更前後で『最も悪化した対面』を一つ選ぶ。そこを補う候補だけを次週の変更にする。", "E-007,E-008,E-009,E-010"),
    M("役割スロットから6体へ落とす", "抽象的な役割を、候補・技・持ち物・検証条件の6体へ変換する。", "構築の組立", (
        ("役割", "主役・速度・支援・対面・保険・情報", "空欄を見える化"),
        ("候補", "種族・特性・技の組み合わせ", "候補2〜3体"),
        ("検証", "一つの仮説に一つの試験", "変更を一度に増やさない")),
        "候補を選んだら、1体ごとに『誰と出すか』『何を守るか』『どの対面で出さないか』を書く。ポケモン名を埋めることが完成ではなく、4体選出で機能することが完成条件。",
        "役割が重なる6体は強そうに見えて、同じ支援を失った時に崩れる。重複は保険か、過剰かを選出表で確認する。",
        "6枠の表に、候補2体・主要な相方・想定対面・テスト結果の4列を加える。1枠だけ差し替え、同じ対面を再テストする。"),
    M("テストを一変数にする", "構築変更の効果を、結果ではなく比較可能な条件で測る。", "実験設計", (
        ("固定", "相手の並びと自分の問い", "一度に変えない"),
        ("変数", "1枠・1技・1選出", "変更を明示"),
        ("判定", "成功条件と失敗条件", "次の行動へ変換")),
        "『火力不足』と感じたとき、アタッカーを変える前に同じ初手で対象選択だけを変える。KOが増えたのか、位置が良くなったのか、勝ち筋の種類を分けて測る。",
        "同時に2体・技・持ち物を変えると、どれが効いたか分からなくなる。強いアイデアを弱い検証にしないため、変更ログを必ず残す。",
        "仮説・変更・固定条件・観察指標・次の決定を5欄に書き、3試合以上同じ条件で試す。"),
    M("対面マトリクスを作る", "苦手な相手の名前を並べるのではなく、相手の勝ち筋と自分の回答を対応させる。", "対策の優先順位", (
        ("相手の軸", "高速・低速・天候・積み・範囲", "種族だけで分類しない"),
        ("自分の回答", "初手・後発・温存", "複数の回答を持つ"),
        ("不確実", "未確認の技・速度", "安全な観察手")),
        "相手にMega Charizard Yがいるとしても、天候だけでなく、Whimsicottの速度操作、Garchompの地面打点、二体の守るを一緒に読む。対面表には『相手の最初の目的』を置く。",
        "種族相性表だけを埋めると、実際の選出・技・速度操作で崩れる。回答はタイプではなく、相手の勝ち筋を一手遅らせる行動で書く。",
        "想定対面を4つ選び、初手2組・後発2体・捨てる枠・観察する情報を一行ずつ入れる。空欄は次の練習テーマにする。"),
    M("大会運用をチェックリスト化する", "登録、機器、通信、試合間、結果確認を、当日に考えずに実行する。", "大会当日", (
        ("前", "更新・Battle Team・アカウント", "開始前に固定"),
        ("中", "対戦・記録・休憩・問い合わせ", "操作を急がない"),
        ("後", "結果・報酬・リンク維持", "受領まで確認")),
        "Handbookは、最新パッチ、互換性のある機器、接続、Battle Team、Team IDなどを競技者の責任として扱う。大会直前に新しい技を試さず、検証済みの最終版を固定する。［事実:E-004］",
        "通信トラブルやルール表示の違和感を、自己判断で再接続・移動・編集しない。運営やJudgeへの問い合わせ条件を事前に書いておく。［事実:E-004］",
        "前日・開始前・試合間・終了後の4チェックリストを作る。実行できない項目が出たら、対戦より運営への確認を優先する。", "E-004"),
]


PLANS = [
    {
        "name": "A 先手圧力",
        "thesis": "Electric Terrain・速度・先制で相手の最初の選択肢を減らし、場が切れても後発で再展開する。",
        "core": "Mega Raichu X候補。公式のElectric Surge紹介は採用の出発点であり、M-Cでの合法性・仕様は大会前に再確認する。［E-007,E-011］",
        "slots": [
            ("主役", "Mega Raichu X", "場と高速物理圧力", "先手が取れない時の守る"),
            ("先手補助", "Fake Out候補", "最初の1ターンを買う", "状態・タイプ確認"),
            ("速度", "Tailwind候補", "場なしでも速くする", "起動役を温存"),
            ("回復/支援", "redirect・回復候補", "主役を再展開", "集中攻撃への回答"),
            ("対面回答", "地面・草・天候への枠", "主役が苦手な盤面", "候補を固定しない"),
            ("後発", "場が消えた後の勝ち筋", "終盤の確定行動", "主役依存を減らす"),
        ],
        "tests": ["先手が取れるが相手が守る", "Electric Terrainを上書きされる", "主役を選出しない後発勝ち"],
        "replace": "速度枠を支援枠に差し替え、先手の再現性と終盤の耐久を比較する。",
        "evidence": "E-007,E-011",
    },
    {
        "name": "B 低速・切り返し",
        "thesis": "Trick Room・redirect・積みを一つの起動手順にし、起動しない選出も同じ6体から選べるようにする。",
        "core": "Mega Mawile／Mega Emboar候補。公式例のEmboar＋Primarina＋Sinistchaは、支援が主役のターンを買う教材。現行規則は別途確認する。［E-008,E-010］",
        "slots": [
            ("主役", "Mega Mawile／Mega Emboar", "低速火力・積み", "単体集中への回答"),
            ("起動", "Trick Room候補", "順番を反転", "起動失敗後の仕事"),
            ("redirect", "Rage Powder／Follow Me候補", "起動を守る", "範囲技への回答"),
            ("特殊打点", "Primarina候補", "物理偏重を補う", "積みとProtect"),
            ("速い補助", "Weavile／Aerodactyl候補", "起動なしの出口", "Fake Out/Tailwind"),
            ("対面保険", "Garchomp等の候補", "天候・飛行への回答", "合法性確認"),
        ],
        "tests": ["Trick Room起動成功", "起動役が集中される", "相手も遅いので起動しない"],
        "replace": "起動役を速い補助へ差し替え、起動なしの勝率ではなく、判断の安定性を比較する。",
        "evidence": "E-008,E-010",
    },
    {
        "name": "C 条件操作",
        "thesis": "Contrary・強化・回復・pivotを重ね、即時KOではなく毎ターンの盤面価値を積み上げる。",
        "core": "Mega Malamar候補。公式記事のContrary engineは、強化の回数より、支援で強化ターンを守る設計を学ぶ教材。［E-009］",
        "slots": [
            ("主役", "Mega Malamar", "強化と持久", "早期集中への回答"),
            ("回復", "Hospitality候補", "場に戻った価値", "回復量を測る"),
            ("pivot", "Parting Shot等の候補", "相手の火力を下げる", "交代先を決める"),
            ("速度", "Scary Face等の候補", "強化後の順番", "素の速度も確認"),
            ("天候回答", "天候を消す候補", "相手の増幅を止める", "場の再設定"),
            ("即時圧力", "強化なしでも攻撃", "積めない試合の出口", "選出を分ける"),
        ],
        "tests": ["強化0回で戦う", "強化1回で維持", "強化を急がず交代"],
        "replace": "即時圧力枠を速度支援へ差し替え、強化できない試合の負け筋を減らす。",
        "evidence": "E-009",
    },
    {
        "name": "D バランス・主軸差し替え",
        "thesis": "主軸を一体に固定せず、共通の速度・支援・対面回答を残して、相手に応じて勝ち筋を変える。",
        "core": "Mega Raichu X／Mega Mawile／Mega Malamar／Mega Emboar候補。公式戦略記事の複数例を役割の比較材料にし、使用率やM-C合法性の根拠にはしない。［E-007〜E-010］",
        "slots": [
            ("主軸1", "Raichu X候補", "場と先手圧力", "逆順・場の上書き"),
            ("主軸2", "Mawile／Malamar候補", "低速・条件操作", "火力または強化前の不足"),
            ("主軸3", "Emboar候補", "Bulk Up・耐久", "中速の順番"),
            ("共通速度", "Tailwind／Trick Room候補", "主軸に合わせる", "両方の出口"),
            ("共通支援", "Fake Out・redirect候補", "主軸の一手", "重複を検証"),
            ("対面回答", "草・電気・天候への枠", "差し替えの弱点", "2回答を目指す"),
        ],
        "tests": ["主軸1で速い相手", "主軸2で場の取り合い", "主軸3で低速盤面"],
        "replace": "主軸を一体ずつ変更し、共通枠が本当に機能しているか、対面マトリクスを更新する。",
        "evidence": "E-007,E-008,E-009,E-010",
    },
]


WEEKLY_FOCUS = [
    ("入口確認", "公式の年齢区分・rating zone・次のGlobal Challenge月を確認", "公式リンクの更新日とゲーム内表示を一致", "未発表日程を仮置きしない"),
    ("登録導線", "Online Competitionsの登録画面を一度開き、必要なIDを確認", "登録前チェック4欄を埋める", "個人情報を公開ログへ貼らない"),
    ("ルール読解", "HandbookのBattle Team・regulation・Double Battle部分を読む", "現行規則の確認先を一行で言う", "古いシーズンの数字を使わない"),
    ("盤面記号", "自分と相手の4体を紙に置き、攻撃対象を矢印で示す", "対象選択を3案比較", "種族名だけで相性を決めない"),
    ("Protect", "守る・集中・分散を同じ初手で比較", "相手の守るで残る盤面を記録", "KOだけを成功基準にしない"),
    ("速度", "速度操作あり・なし・逆順の3盤面を再生", "順番を変える情報を特定", "同速を都合よく固定しない"),
    ("支援", "Fake Out・redirect・回復の一手の価値を比較", "支援役の仕事を一文で説明", "支援を火力不足と呼ばない"),
    ("選出", "想定相手3体に初手2＋後発2を作る", "選ばない2体の役割も書く", "6体全部を入れようとしない"),
    ("A案試用", "先手圧力案の場・速度・後発をテスト", "場なしでも残る出口を確認", "先手確定と仮定しない"),
    ("A案反証", "相手の守る・速度操作・場上書きを入れる", "最初に崩れる枠を特定", "全枠を同時に変えない"),
    ("B案試用", "低速切り返しの起動成功と失敗を再生", "起動しない選出を一つ作る", "Trick Room固定にしない"),
    ("B案反証", "起動役への集中・挑発・相手低速を試す", "主役の攻撃開始条件を記録", "遅いから常に有利ではない"),
    ("C案試用", "強化0・1・2回の3状態を比べる", "強化を急がない価値を測る", "積み回数を勝率と混同しない"),
    ("C案反証", "天候・pivot・強制交代を入れる", "強化前の出口を一つ残す", "主役を早く失わない"),
    ("D案試用", "主軸3候補を同じ役割表に置く", "共通枠の機能を比較", "主軸の知名度で選ばない"),
    ("対面表", "高速・低速・範囲・積みの4軸で相手を分類", "各軸に回答2つを置く", "タイプ表だけにしない"),
    ("ログ", "リプレイ1本を観測・判断・結果に分ける", "最初に勝ち筋が変わったターンを特定", "最後のKOだけを直さない"),
    ("一変数", "1枠または1技だけを変更して3試合", "変更の因果を説明", "複数変更を避ける"),
    ("主役温存", "主役を選出しない後発勝ちを試す", "主役依存の度合いを測る", "主役なしを諦めない"),
    ("場管理", "場・天候・速度操作の切替タイミングを記録", "場を使う条件と温存条件", "場の存在だけで勝てると考えない"),
    ("時間", "1時間内に問いを一つだけ実験", "開始・停止・次週の手順", "対戦数を目的にしない"),
    ("大会告知", "公式大会ページとゲーム内ニュースを再確認", "変更点を台帳へ", "古い日付を残さない"),
    ("チーム確認", "Team Listに必要な項目を列挙", "技・特性・持ち物の照合", "記事のセットを合法性と混同しない"),
    ("通信", "更新・機器・接続・アカウントを確認", "問い合わせ条件を決める", "自己判断で編集しない"),
    ("結果", "ランキング・報酬・CPリンクの確認手順を練習", "終了後の画面を確認", "参加とCPを同一視しない"),
    ("再試験", "最も悪化した対面を同じ条件で再実験", "改善が1変数で説明できる", "全案を捨てない"),
    ("構築会議", "A〜Dの4案を同じ6軸で採点", "候補を一枠だけ移す", "点数の合計だけで決めない"),
    ("第2案", "主軸を差し替え、初手4組を再作成", "共通枠の意味を確認", "ただのコピーをしない"),
    ("実戦準備", "最終候補を練習用と大会用に分離", "固定日を決める", "直前改造を止める"),
    ("模擬登録", "登録から結果確認までを時間計測", "詰まった操作を修正", "個人情報を保存しすぎない"),
    ("模擬大会", "試合間の停止条件・記録・休憩を実行", "再開条件を守る", "連敗で即改造しない"),
    ("最終更新", "公式発表を差分監査し、未発表欄を更新", "変わった章だけ特定", "本全体を読み直す必要はない"),
    ("提出前", "Battle Team・Team List・機器・アカウントを最終確認", "空欄ゼロのチェック", "未確認は参加を急がない"),
    ("大会後", "結果をログ化し、次のGlobal Challengeへ引き継ぐ", "一つの改善テーマ", "結果を人格評価にしない"),
    ("次の一周", "大会後の変更を一枠だけ試し、次の公式発表へ備える", "変更理由と再試験条件が残る", "結果だけで全構築を捨てない"),
]


APPENDIX_PAGES = [
    ("4案の比較表", "4つの案を、主役・速度・支援・勝ち筋・崩れ方・初心者向けの練習順で比較する。"),
    ("A案の調整カード", "場を作る候補、先手補助、後発、場なしの勝ち筋を一枚で更新する。"),
    ("B案の調整カード", "起動成功、起動失敗、相手低速の3分岐を一枚で更新する。"),
    ("C案の調整カード", "強化回数ではなく、維持ターンと回復・pivotを記録する。"),
    ("D案の調整カード", "主軸差し替え前後で共通枠・対面回答・選出を比較する。"),
    ("役割スロット記入票", "主役、速度、支援、対面、保険、情報の候補を3体ずつ書く。"),
    ("選出4体の検証票", "初手2体、後発2体、相手の返し、次ターンの出口を記録する。"),
    ("対面マトリクス", "高速・低速・範囲・積み・天候・場の6軸を縦横に置く。"),
    ("1ターン比較票", "候補A/B/Cと相手の最善応答、2ターン後の残りを記録する。"),
    ("リプレイ因果票", "観測、判断、結果、分類、次の実験を一試合分残す。"),
    ("構築変更ログ", "変更前、変更内容、固定条件、観測結果、採否、次の仮説を記録する。"),
    ("大会前チェック", "規則・対象・アカウント・Battle Team・Team List・機器を確認する。"),
    ("試合間カード", "停止条件、休憩、次の問い、再開条件を記入する。"),
    ("証拠台帳 1", "E-001〜E-004を、主張・参照箇所・確認日・リンク付きで示す。"),
    ("証拠台帳 2", "E-005〜E-009を、Global Challengeと4案の設計根拠として示す。"),
    ("証拠台帳 3", "E-010〜E-013を、公式チーム例・ニュース・更新窓口として示す。"),
    ("公式発表の差分票", "新告知で変わった日付、形式、対象、報酬、登録窓口を記録する。"),
    ("未発表情報の扱い", "推測で埋めず、発表後に更新する章と影響範囲を記入する。"),
    ("用語 1", "Battle Team、Team List、rating zone、CP、regulation setを説明する。"),
    ("用語 2", "Protect、redirect、速度操作、範囲技、pivotを盤面で説明する。"),
    ("用語 3", "主役、支援、後発、保険、対面回答、勝ち筋を役割表で説明する。"),
    ("35週の再利用法", "週を飛ばした場合の縮退メニューと、同じ週を再試験する条件を示す。"),
    ("読者の質問ログ", "分からなかった言葉、公式で確認するURL、次の練習を記録する。"),
    ("索引：ポケモンと役割", "Raichu X、Mawile、Malamar、Emboarなどを役割と出典から探す。"),
    ("索引：判断と更新", "守る、速度、選出、合法性、公式発表、登録の参照先を探す。"),
    ("公式掲載チーム例を読む", "Mega Emboar、Primarina、Sinistcha、Weavile、Aerodactyl、Garchompの掲載セットを教材として分解する。"),
    ("公式例の仮想ケース", "公式例の技・特性・持ち物を使い、Mega Charizard Y＋Whimsicottを相手に2ターンを再生する。現行ルールでの合法性は別途確認する。"),
]


def weekly_dates(start: date = date(2026, 10, 3), count: int = 35) -> list[date]:
    return [start + timedelta(days=7 * i) for i in range(count)]


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("。", "").replace("、", "")


def validate_source() -> None:
    if len(MODULES) != 35:  # pragma: no cover
        raise ValueError(f"expected 35 modules, got {len(MODULES)}")
    if len(PLANS) != 4:  # pragma: no cover
        raise ValueError("four party plans are required")
    if len(WEEKLY_FOCUS) != 35:  # pragma: no cover
        raise ValueError(f"expected 35 weeks, got {len(WEEKLY_FOCUS)}")
    titles = [m.title for m in MODULES]
    if len(set(titles)) != len(titles):  # pragma: no cover
        raise ValueError("module titles must be unique")
    seen: set[str] = set()
    for module in MODULES:
        for text in (module.goal, module.case, module.counter, module.lab):
            key = normalize(text)
            if key in seen:  # pragma: no cover
                raise ValueError(f"duplicate topic text: {module.title}")
            seen.add(key)
        if not module.rows:  # pragma: no cover
            raise ValueError(f"no role table: {module.title}")
    ids = {row[0] for row in EVIDENCE}
    for plan in PLANS:
        for evidence_id in re.findall(r"E-\d{3}", plan["core"]):
            if evidence_id not in ids:  # pragma: no cover
                raise ValueError(f"unknown evidence ID: {evidence_id}")
    if len(APPENDIX_PAGES) != 27:  # pragma: no cover
        raise ValueError("the appendix must contain 27 topic-specific pages")


def find_font() -> str:
    result = subprocess.run(["fc-match", "-f", "%{file}", "BIZ UDGothic"], check=True, capture_output=True, text=True)
    path = result.stdout.strip()
    if not path or not Path(path).exists():  # pragma: no cover
        raise RuntimeError("BIZ UDGothic is required for Japanese PDF output")
    return path


def wrap_text(text: str, font, size: float, width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and font.stringWidth(candidate, "JP", size) > width:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def draw_wrapped(canvas, text: str, x: float, y: float, width: float, font, size: float = 9.2, leading: float = 13.2, color=(0.12, 0.15, 0.20)) -> float:
    canvas.setFont("JP", size)
    canvas.setFillColorRGB(*color)
    for line in wrap_text(text, font, size, width):
        if y < BOTTOM + 24:  # pragma: no cover
            raise RuntimeError("page overflow while rendering text")
        canvas.drawString(x, y, line)
        y -= leading
    return y


def draw_table(canvas, rows: Sequence[Sequence[str]], x: float, y: float, widths: Sequence[float], font, size: float = 7.4, leading: float = 9.4, header: bool = True) -> float:
    cell_padding = 5
    prepared: list[list[list[str]]] = []
    for row in rows:
        wrapped = [wrap_text(str(cell), font, size, width - cell_padding * 2) for cell, width in zip(row, widths)]
        prepared.append(wrapped)
    for row_index, wrapped_row in enumerate(prepared):
        row_height = max(len(cell) for cell in wrapped_row) * leading + cell_padding * 2
        if y - row_height < BOTTOM + 30:  # pragma: no cover
            raise RuntimeError("page overflow while rendering table")
        x_cursor = x
        for col_index, cell_lines in enumerate(wrapped_row):
            width = widths[col_index]
            fill = (0.10, 0.22, 0.38) if header and row_index == 0 else ((0.93, 0.96, 0.98) if row_index % 2 == 0 else (1, 1, 1))
            canvas.setFillColorRGB(*fill)
            canvas.setStrokeColorRGB(0.70, 0.76, 0.82)
            canvas.rect(x_cursor, y - row_height, width, row_height, fill=1, stroke=1)
            canvas.setFillColorRGB(1, 1, 1) if header and row_index == 0 else canvas.setFillColorRGB(0.12, 0.15, 0.20)
            canvas.setFont("JP", size)
            line_y = y - cell_padding - leading + (leading if header and row_index == 0 else 0)
            for line in cell_lines:
                canvas.drawString(x_cursor + cell_padding, line_y, line)
                line_y -= leading
            x_cursor += width
        y -= row_height
    return y


def footer(canvas, page_number: int, section: str) -> None:
    canvas.setStrokeColorRGB(0.76, 0.80, 0.84)
    canvas.line(MARGIN, 27, PAGE_WIDTH - MARGIN, 27)
    canvas.setFont("JP", 7.5)
    canvas.setFillColorRGB(0.35, 0.40, 0.46)
    canvas.drawString(MARGIN, 15, f"PJCS2027 実践ワークブック｜{section}")
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 15, str(page_number))


def page(canvas, page_number: int, section: str, title: str, kicker: str, blocks: Sequence[tuple[str, object]], font, outline: str | None = None, outline_level: int = 0) -> None:
    bookmark = f"page-{page_number}"
    canvas.bookmarkPage(bookmark)
    if outline:
        canvas.addOutlineEntry(outline, bookmark, level=outline_level, closed=False)
    canvas.setFillColorRGB(0.96, 0.98, 1)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.setFillColorRGB(0.10, 0.22, 0.38)
    canvas.rect(0, PAGE_HEIGHT - 78, PAGE_WIDTH, 78, fill=1, stroke=0)
    canvas.setFillColorRGB(0.78, 0.91, 0.98)
    canvas.setFont("JP", 8.2)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 26, kicker)
    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("JP", 17)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 54, title)
    y = PAGE_HEIGHT - 103
    for kind, value in blocks:
        if kind == "label":
            canvas.setFillColorRGB(0.10, 0.45, 0.56)
            canvas.setFont("JP", 9.4)
            canvas.drawString(MARGIN, y, str(value))
            y -= 17
        elif kind == "text":
            y = draw_wrapped(canvas, str(value), MARGIN, y, CONTENT_WIDTH, font)
            y -= 8
        elif kind == "small":  # pragma: no cover
            y = draw_wrapped(canvas, str(value), MARGIN, y, CONTENT_WIDTH, font, size=8.0, leading=11.0, color=(0.25, 0.29, 0.35))
            y -= 6
        elif kind == "table":
            rows, widths = value
            y = draw_table(canvas, rows, MARGIN, y, widths, font)
            y -= 10
        elif kind == "lines":
            labels = list(value)
            canvas.setFont("JP", 8.6)
            canvas.setFillColorRGB(0.20, 0.24, 0.30)
            for label in labels:
                if y < BOTTOM + 42:  # pragma: no cover
                    raise RuntimeError("page overflow while rendering worksheet")
                canvas.drawString(MARGIN, y, str(label))
                canvas.setStrokeColorRGB(0.55, 0.62, 0.69)
                canvas.line(MARGIN, y - 8, PAGE_WIDTH - MARGIN, y - 8)
                y -= 28
        elif kind == "toclinks":
            canvas.setFont("JP", 9.0)
            for label, target_page in value:
                if y < BOTTOM + 36:  # pragma: no cover
                    raise RuntimeError("page overflow while rendering table of contents")
                bookmark = f"page-{target_page}"
                canvas.setFillColorRGB(0.06, 0.28, 0.58)
                canvas.drawString(MARGIN, y, f"{label}  …… p.{target_page}")
                canvas.linkRect("", bookmark, (MARGIN, y - 4, PAGE_WIDTH - MARGIN, y + 9), relative=0, thickness=0)
                y -= 20
        else:  # pragma: no cover
            raise ValueError(f"unknown block type: {kind}")
    # This is a deliberate workbook area, not an accidental empty page.  It
    # gives the reader a place to record the observation produced by the page.
    if y > BOTTOM + 95:
        box_top = y - 8
        box_bottom = BOTTOM + 34
        canvas.setFillColorRGB(1, 1, 1)
        canvas.setStrokeColorRGB(0.70, 0.76, 0.82)
        canvas.roundRect(MARGIN, box_bottom, CONTENT_WIDTH, box_top - box_bottom, 5, fill=1, stroke=1)
        canvas.setFillColorRGB(0.10, 0.45, 0.56)
        canvas.setFont("JP", 8.0)
        canvas.drawString(MARGIN + 8, box_top - 15, "このページの観察メモ")
        canvas.setStrokeColorRGB(0.84, 0.87, 0.89)
        line_y = box_top - 33
        while line_y > box_bottom + 12:
            canvas.line(MARGIN + 8, line_y, PAGE_WIDTH - MARGIN - 8, line_y)
            line_y -= 22
    footer(canvas, page_number, section)
    canvas.showPage()


def source_page(canvas, page_number: int, title: str, entries: Sequence[tuple[str, str, str, str, str]], font) -> None:
    """Render linked evidence entries without squeezing URLs into a table."""
    bookmark = f"page-{page_number}"
    canvas.bookmarkPage(bookmark)
    canvas.addOutlineEntry(title, bookmark, level=1, closed=False)
    canvas.setFillColorRGB(0.96, 0.98, 1)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.setFillColorRGB(0.10, 0.22, 0.38)
    canvas.rect(0, PAGE_HEIGHT - 78, PAGE_WIDTH, 78, fill=1, stroke=0)
    canvas.setFillColorRGB(0.78, 0.91, 0.98)
    canvas.setFont("JP", 8.2)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 26, "付録｜証拠台帳")
    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("JP", 17)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 54, title)
    y = PAGE_HEIGHT - 103
    for evidence_id, kind, source_title, supports, url in entries:
        canvas.setFillColorRGB(0.10, 0.45, 0.56)
        canvas.setFont("JP", 10)
        canvas.drawString(MARGIN, y, f"{evidence_id}｜{kind}｜{source_title}")
        y -= 16
        y = draw_wrapped(canvas, supports, MARGIN, y, CONTENT_WIDTH, font, size=8.0, leading=10.5)
        y -= 2
        url_lines = wrap_text(url, font, 7.2, CONTENT_WIDTH)
        canvas.setFont("JP", 7.2)
        canvas.setFillColorRGB(0.06, 0.28, 0.58)
        first_y = y
        for line in url_lines:
            canvas.drawString(MARGIN, y, line)
            y -= 9.2
        canvas.linkURL(url, (MARGIN, y, PAGE_WIDTH - MARGIN, first_y + 4), relative=0)
        y -= 10
        if y < BOTTOM + 36:  # pragma: no cover
            raise RuntimeError("evidence page overflow")
    footer(canvas, page_number, "付録")
    canvas.showPage()


def build_pdf(output: Path) -> int:
    validate_source()
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.colors import HexColor
    except ImportError as exc:  # pragma: no cover - exercised by the CLI environment, not source validation
        raise RuntimeError("install reportlab with: uv run --with 'reportlab==5.0.1' python tools/build_pjcs2027_playbook.py") from exc

    font_path = find_font()
    pdfmetrics.registerFont(TTFont("JP", font_path, subfontIndex=0))
    font = pdfmetrics
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep timestamps and document IDs stable so a rebuild is byte-reproducible
    # when the same pinned ReportLab/font environment is used.
    canvas = pdf_canvas.Canvas(str(output), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1, invariant=1)
    canvas.setTitle("Pokémon Champions 2027 Global ChallengeからPJCS2027へ")
    canvas.setAuthor("thinking-publication")
    canvas.setSubject("初心者向けダブルバトル、複数パーティ案、週1時間の実践計画")
    page_number = 1

    front = [
        ("表紙", "Pokémon ChampionsからPJCS2027へ", "所持ポケモン不問・ダブルバトル初心者向けの実践ワークブック", [("text", "2026年10月〜2027年5月｜週1日・1時間｜4つのパーティ案を比較し、公式情報の更新に合わせて調整する。"), ("lines", ["名前／開始日", "いまの経験と困っていること", "この本を読み終えた時にできたいこと"])]),
        ("目次", "この本の全体像", "35章・35週・4案・27付録を、目的から選ぶ", [("table", ([['区分', '内容', '到達点'], ['第I部', '参加・情報・登録（1〜6章）', '公式情報と参加準備を確認できる'], ['第II部', '判断・ダブル盤面（7〜24章）', '1ターンと4体選出を説明できる'], ['第III部', '構築・4つの案（25〜35章）', '一枠ずつ調整できる'], ['35週', '2026-10-03〜2027-05-29', '週1時間の問いを実行できる'], ['付録', '記録票・証拠・用語・索引', '更新と再利用ができる']], [70, 200, 140])), ("toclinks", [("第1章｜参加ルート", 11), ("35週カレンダー", 186), ("A 先手圧力｜設計図", 256), ("付録｜記録と証拠", 300)]), ("text", "ページ番号は生成後に確定する。PDFのしおりと上のリンクから各部へ直接移動できる。")]),
        ("読者契約", "この本が約束すること、約束しないこと", "結果を保証せず、判断と更新の手順を保証する", [("text", "本書は大会の出場権や勝利を保証しない。公式発表、現在の規則、登録情報、対戦結果、通信環境で結果は変わる。代わりに、初心者が『何を確認し、何を練習し、どこを一つだけ変えるか』を再現できる形にする。"), ("table", ([['約束する', '約束しない'], ['一次情報へ辿れる証拠ID', '将来の未発表条件の断定'], ['4案を調整する比較手順', '特定候補の現在の強さ'], ['週1時間の実行メニュー', '出場権獲得の保証']], [205, 205]))]),
        ("ルート", "最初に見る地図", "確定・更新対象・個人確認を別の欄へ置く", [("text", "公式案内では、PJCS2027の対象はゲーム内の国・地域設定と居住国が日本であること、各カテゴリ上位120名、権利を得たアカウントの継続利用で管理される。Mastersは2010年以前生まれ。Global Challenge III〜VIと5月予選の細部は後日発表なので、確定情報と更新対象を混ぜない。［事実:E-001］"), ("table", ([['層', 'この本で行うこと'], ['確定', '根拠を読み、練習へ変換する'], ['個人確認', 'ゲーム内の国・地域、居住国、アカウントを確認する'], ['更新対象', '公式発表後に形式・試合数・対象人数を差分反映する']], [100, 310]))]),
        ("使い方", "まず目次を選び、全部を順番に読まない", "今週の問いから必要な章へ入る", [("text", "毎週は『今週の問い→必要な前提→25分の試行→短い記録→次週の一変更』で進める。勝率が動かない週も、情報の確認や対戦後の分類ができれば前進である。"), ("table", ([['困りごと', '読む場所'], ['登録・合法性', '第1〜6章、付録のチェック票'], ['盤面・選出', '第7〜24章、1ターン比較票'], ['構築の調整', '第25〜32章、4案の調整カード'], ['時間がない', '35週カレンダーの縮退メニュー']], [150, 260]))]),
        ("証拠", "証拠IDの読み方", "事実・推論・考察・未発表を明示する", [("text", "本文の［事実:E-004］は、巻末のE-004から一次情報へ辿れることを示す。［考察］は筆者の設計判断、［未発表］は公式発表前に確定していない事項である。二次記事は導線として使えても、規則の代替にはしない。"), ("table", ([['表示', '読者の行動'], ['事実', 'リンクの参照箇所と日付を見る'], ['推論', '前提が変わると結論も変わると理解する'], ['考察', '自分の環境で小さく試す'], ['未発表', '公式発表後に更新する']], [100, 310]))]),
        ("4案", "4つのパーティ案を先に比較する", "所持ポケモンではなく、勝ち筋の違いから選ぶ", [("table", ([['案', '主な考え方', '最初の検証'], ['A', '先手圧力', '場・速度・後発'], ['B', '低速切り返し', '起動成功・失敗・起動なし'], ['C', '条件操作', '強化を急がず維持'], ['D', 'バランス差し替え', '主軸を替えても共通枠が機能']], [55, 190, 165])), ("text", "最初から一案に固定しない。各案を同じ6軸で採点し、最も悪化した対面を次の練習テーマにする。候補の合法性は大会時点で必ず確認する。")]),
        ("開始チェック", "今週の60分を予約する", "先に空欄と停止条件を決める", [("lines", ["今週の問い（1文）", "確認する公式URLと確認日", "試す盤面またはリプレイ", "終了時に残す一つの成果物", "対戦を止める条件"])]),
        ("凡例", "本書の表とワークシート", "書き込める余白を練習の一部にする", [("text", "表の『候補』はまだ採用を意味しない。『確認』が済んだものだけ大会用へ移す。ワークシートの空欄は、考えがないのではなく、次に観察する情報を指定するために残す。"), ("lines", ["今日見えた事実", "まだ分からないこと", "次に変えるのは一つだけ"])]),
        ("版情報", "更新できる本として使う", "将来の公式発表を本文へ戻す", [("text", "基準日：2026年10月3日。2027 Global Challenge Iの実施後であり、次の開催月・ルール・PJCS2027予選の細部は公式ページとゲーム内ニュースで更新する。更新した章、変更理由、参照URLを付録の差分票へ残す。［E-002,E-005,E-013］"), ("lines", ["次回確認日", "更新したURL", "変更した章と判断への影響"])]),
    ]
    for section, title, kicker, blocks in front:
        page(canvas, page_number, section, title, kicker, blocks, font, outline=f"{section}｜{title}")
        page_number += 1

    for index, module in enumerate(MODULES, start=1):
        evidence = f"［参照: {module.evidence}］" if module.evidence else ""
        page(canvas, page_number, f"第{index}章", module.title, module.lens, [
            ("label", "この章の到達点"), ("text", module.goal + evidence),
            ("label", "判断の材料"), ("text", module.case),
            ("label", "前提を外したとき"), ("text", module.counter),
            ("lines", ["自分の言葉で言い換える", "この章を使う相手の並び"]),
        ], font, outline=f"第{index}章｜{module.title}"); page_number += 1
        page(canvas, page_number, f"第{index}章", f"{module.title}｜比較表", "一つの情報で選択を変える", [
            ("text", f"{module.title}では、{module.rows[0][0]}を確定情報として扱えるかが最初の分岐になる。次に、{module.rows[1][0]}を仮説として残し、最後に{module.rows[2][0]}を保険として書く。下表は答えではなく、対戦前に埋める観察欄である。"),
            ("table", ([['見る対象', '採用する判断', '残す注意点'], *module.rows], [105, 185, 120])),
            ("lines", ["この表でまだ空欄の情報", "空欄のままでも選べる安全手"]),
        ], font); page_number += 1
        page(canvas, page_number, f"第{index}章", f"{module.title}｜ケース再生", "具体的な盤面で2ターン先まで書く", [
            ("label", "ケース"), ("text", module.case),
            ("label", "再生手順"), ("text", f"{module.title}の盤面で、①見えていた事実を3つ書く。②候補をA/B/Cで並べる。③相手の最善応答を一つ置く。④2ターン後に残る勝ち筋を比較する。"),
            ("lines", ["候補Aと相手の返し", "候補Bと相手の返し", "採用した手と理由"]),
        ], font); page_number += 1
        page(canvas, page_number, f"第{index}章", f"{module.title}｜反例と修正", "うまくいかない条件を先に作る", [
            ("label", "反例"), ("text", module.counter),
            ("table", ([['崩れた前提', '観察する合図', '次の修正'], [f'{module.rows[0][0]}の条件を一つに決めつける', '別の回答や分岐が現れる', f'{module.rows[0][0]}の候補を2つ以上残す'], [f'{module.rows[1][0]}の結果だけで評価する', '理由や再現条件が説明できない', f'{module.rows[1][0]}を観測・判断・結果へ戻す'], [f'{module.rows[2][0]}の情報を古いまま使う', '日付・規則・対象が違う', 'E-IDsの確認日を更新']], [135, 150, 125])),
            ("lines", ["今回の反例", "反例が出たときに変える一つ"]),
        ], font); page_number += 1
        page(canvas, page_number, f"第{index}章", f"{module.title}｜1時間ラボ", "練習後に次の週へ成果物を渡す", [
            ("table", ([['時間', '作業', '終了条件'], ['5分', '今日の問いと固定条件を決める', '一文で言える'], ['10分', '必要な公式情報・盤面を確認', '未確認欄が分かる'], ['25分', module.lab, '同じ条件を3回試す'], ['10分', '結果を観測・判断・結果に分類', '原因候補が一つ'], ['10分', '次週の一変更を決める', '変更ログへ残る']], [45, 240, 125])),
            ("label", "成果物"), ("text", module.lab),
            ("lines", ["見えた事実", "次回も固定する条件", "次週に渡す一つの問い"]),
        ], font); page_number += 1

    dates = weekly_dates()
    for week, (week_date, (focus, task, success, fallback)) in enumerate(zip(dates, WEEKLY_FOCUS), start=1):
        page(canvas, page_number, "35週カレンダー", f"第{week:02d}週｜{focus}", week_date.strftime("%Y-%m-%d（土）｜週1日・1時間"), [
            ("label", "今週の目的"), ("text", task),
            ("table", ([['時間', '実行'], ['10分', '問いを一つにし、必要な前提だけ確認'], ['25分', task + 'を同じ条件で試す'], ['15分', '記録を観測・判断・結果に分ける'], ['10分', '次週へ一つだけ引き継ぐ']], [45, 365])),
            ("label", "合格ライン"), ("text", success),
            ("label", "対戦できない日の縮退"), ("text", fallback + "。仮想盤面またはリプレイ1本で同じ問いを実行する。"),
        ], font, outline=f"第{week:02d}週｜{focus}"); page_number += 1
        page(canvas, page_number, "35週カレンダー", f"第{week:02d}週｜記録シート", "結果ではなく再現条件を残す", [
            ("text", f"日付：{week_date.isoformat()}｜焦点：{focus}\n今週の作業は『{task}』。合格ラインは『{success}』であり、対戦できない場合は『{fallback}』へ縮退する。勝敗より、この条件を次週へ再現できる記録を残す。"),
            ("lines", ["見えていた事実を3つ", "候補A／B／C", "相手の最善応答", "最初に崩れた前提", "採用する一つの変更", "次週へ残さない作業"]),
        ], font); page_number += 1

    for plan in PLANS:
        name = plan["name"]
        page(canvas, page_number, "パーティ案", f"{name}｜設計図", "所持ポケモン不問・役割から候補へ", [
            ("label", "勝ち筋"), ("text", plan["thesis"]),
            ("label", "公式情報との距離"), ("text", plan["core"]),
            ("table", ([['役割', '候補', '仕事', '失敗時の確認'], *plan["slots"]], [75, 125, 145, 120])),
        ], font, outline=f"{name}｜設計図"); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜初手と後発", "4体選出を主役の都合から切り離す", [
            ("table", ([['相手の軸', '初手2体', '後発2体', '捨てる情報'], ['高速圧力', '支援＋主役', '保険＋後発', '相手の未知技'], ['低速・起動', '起動＋守る役', '主役＋保険', '一手目の火力'], ['範囲攻撃', '分散回答＋主役', '回復＋対面', '単体KOの誘惑'], ['積み・長期戦', '観察役＋支援', '主役＋終盤', '早期の強化回数']], [105, 105, 105, 150])),
            ("text", f"{name}の表は完成した選出ではない。相手の6体を見た時、初手の役割と後発の役割が重複していないかを一行で説明する。"),
            ("lines", ["この案の初手候補1", "この案の初手候補2", "後発へ残す理由"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜3つのテスト", "同じ6体で条件だけを変える", [
            ("table", ([['テスト', '相手の行動', '観察点'], ["1：理想展開", plan["tests"][0], "勝ち筋が何ターン続くか"], ["2：反証", plan["tests"][1], "最初に崩れる役割"], ["3：主役不在", plan["tests"][2], "残り5体からの出口"]], [115, 180, 170])),
            ("text", f"{name}の各テストで変更するのは一つだけ。『負けた』ではなく、どの役割が機能しなかったかを記録する。"),
            ("lines", ["理想展開の観察", "反証で崩れた場所", "主役不在の出口"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜枠の調整", "1枠ずつ差し替え、目的を失わない", [
            ("table", ([['変更', '解決したい問題', '悪化し得る問題', '採否'], ['速度枠→支援枠', '先手役が倒れた後', '相手の初手圧力', ''], ['主役→代替主役', '主役への対策', '共通枠の相性', ''], ['持ち物・技候補', 'KO・耐久・命中', '別の対面ライン', '']], [105, 135, 135, 90])),
            ("text", plan["replace"]),
            ("lines", ["変更前の仮説", "3試合後の観察", "次に残す一枠"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜初心者用の操作順", "考える順番を固定して迷いを減らす", [
            ("text", f"{name}の初手前は『相手の勝ち筋→自分の主役→支援の一手→後発の出口』の順に見る。ターン中は『対象→相手の守る／交代→2ターン後』の順に戻る。順番を守れば、知識が不足していても未知を未知として扱える。"),
            ("table", ([['順番', '質問'], ['1', '相手は何を通したいか？'], ['2', '自分は何を残したいか？'], ['3', 'この手が外れたら次は何か？'], ['4', '今週の問いに関係する記録は何か？']], [55, 355])),
            ("lines", ["今日の最初の質問", "今ターンの安全手", "次ターンへ残すポケモン"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜合法性ゲート", "公式例と大会用チームを分ける", [
            ("text", f"{name}の候補は、公式の戦略記事・ニュースを起点にした役割候補である。現行regulation set、対象ポケモン、技・特性・持ち物、Team List、ゲーム内の表示は、大会前に別途確認する。公式例の存在は、現在の大会での合法性や強さを保証しない。［E-004,E-013］"),
            ("lines", ["現行regulation setと確認日", "対象リストのURLまたはゲーム内画面", "Team List照合日", "未確認の候補と扱い"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜初週の1時間", "案を選ぶ前に比較する", [
            ("table", ([['分', '作業', '成果物'], ['10', '勝ち筋を一文にする', '起点→主役→終了'], ['20', '想定相手を2つ再生', '初手と後発'], ['20', '反証を一つ加える', '崩れる役割'], ['10', '一枠の候補を残す', '変更ログ']], [45, 220, 145])),
            ("text", "初週は勝率で案を決めない。『自分が説明しやすい』『負け筋を記録しやすい』『未確認を分離できる』案を選び、翌週に一変数の検証へ進む。"),
            ("lines", ["最初に試す案", "理由", "次週へ渡す問い"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜更新カード", "公式発表があった時に差分だけ直す", [
            ("table", ([['更新対象', '変わったら影響する場所', '確認後の行動'], ['規則セット', '候補・技・持ち物', '合法性ゲートを再実行'], ['大会日程', '週カレンダー', '該当週の目的を差替'], ['CP・登録条件', '参加チェック', '登録カードを更新'], ['公式戦略', '候補の優先度', '役割表は再検証']], [110, 190, 110])),
            ("text", "更新時は本書を全面的に読み直さず、台帳の変更箇所、影響する章、影響しない前提を記録する。更新後のPDFやHTMLにも確認日を残す。［E-005,E-013］"),
            ("lines", ["公式発表のURL", "変更前／変更後", "影響範囲", "再検証の完了日"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜独立レビュー", "自分の理想展開を壊してから採用する", [
            ("text", f"{name}のレビューでは、主役が1ターン目に倒れる、支援役が挑発される、速度操作が逆になる、場が上書きされる、という4つの反証を置く。どれか一つで全てが崩れる案は、強い主役ではなく、狭い勝ち筋として扱う。"),
            ("lines", ["最も危険な反証", "それでも残る一手", "残らない場合の一枠差し替え", "採用／保留"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜採用判定", "構築を選んだ理由を再現可能にする", [
            ("table", ([['基準', '0', '1', '2'], ['勝ち筋を説明', '言えない', '一文で言える', '相手の対策まで言える'], ['選出を説明', '種族で選ぶ', '役割で選ぶ', '分岐まで選べる'], ['反証への出口', 'なし', '一手', '複数の出口'], ['更新可能性', '根拠なし', 'URLあり', '影響範囲まで記録']], [140, 85, 85, 100])),
            ("text", f"{name}は合計点で機械的に決めず、0がある基準を次の練習にする。採用は『強そう』ではなく、『いまの情報で説明・検証・更新ができる』を満たしたときに行う。"),
            ("lines", ["4案の点数", "0を解消する次の実験", "大会用へ移す条件"]),
        ], font); page_number += 1
        page(canvas, page_number, "パーティ案", f"{name}｜引き継ぎ", "次の週に、変更を一つだけ渡す", [
            ("text", f"{name}を使った週の最後に、全てを評価し直さない。最も大きく判断を変えた情報、最も再現できなかった選択、一枠だけの修正候補を残す。次の週はその一つを固定条件として再試験する。"),
            ("lines", ["最も大きかった観察", "捨てる仮説", "次週の固定条件", "次週の一変数", "公式確認が必要なURL"]),
        ], font); page_number += 1

    evidence_rows = [["ID", "区分", "この本で使う範囲"]] + [[item[0], item[1], item[3]] for item in EVIDENCE]
    for i in range(len(APPENDIX_PAGES)):
        title, description = APPENDIX_PAGES[i]
        blocks: list[tuple[str, object]] = [("text", description)]
        if i == 0:
            blocks.append(("table", ([['案', '主役', '勝ち筋', '崩れ方'], ['A', 'Raichu X', '先手・場・後発', '逆順・場上書き'], ['B', 'Mawile/Emboar', '起動・積み', '起動役集中'], ['C', 'Malamar', '強化・維持', '早期集中・強制交代'], ['D', '差替主軸', '共通枠の再利用', '主軸変更で役割崩壊']], [45, 115, 150, 100])))
        elif 13 <= i <= 15:
            start = (i - 13) * 5
            blocks.append(("table", (evidence_rows[0:1] + evidence_rows[1 + start:1 + start + 5], [45, 80, 285])))
            blocks.append(("text", "URLはPDF内のリンク注釈から直接開ける。公開日・版・参照箇所は更新時に再確認し、二次情報は公式情報の代わりにしない。"))
        elif i == 16:
            blocks.append(("table", ([['差分', '確認先', '影響'], ['日程', '公式カレンダー／ゲーム内ニュース', '該当週'], ['形式', '大会ページ／Handbook', '構築・選出'], ['対象', 'HOME／ゲーム内表示', '合法性ゲート'], ['報酬・CP', '公式告知／Access', '登録カード']], [100, 180, 100])))
        elif i in (18, 19, 20):
            blocks.append(("table", ([['語', '初心者の一文'], ['Battle Team', '大会で固定する6体の登録単位'], ['Team List', '提出する情報の基準'], ['redirect', '攻撃対象を別の枠へ向ける支援'], ['pivot', '交代で次の有利な盤面を作る']], [115, 265])))
        elif i == 25:
            blocks.append(("text", "以下は公式のMega Emboar戦略記事に掲載された教材例。技・特性・持ち物・能力値は記事の参照用であり、現行のM-CやPJCS2027予選でそのまま合法とは限らない。［E-004,E-010］"))
            blocks.append(("table", ([['ポケモン', '持ち物／特性', '技の例'], ['Emboar', 'Emboarite／Blaze', 'Heat Crash、Drain Punch、Bulk Up、Protect'], ['Primarina', 'Leftovers／Liquid Voice', 'Hyper Voice、Moonblast、Calm Mind、Protect'], ['Sinistcha', 'Sitrus Berry／Hospitality', 'Matcha Gotcha、Life Dew、Rage Powder、Trick Room'], ['Weavile', "King's Rock／Pickpocket", 'Knock Off、Ice Spinner、Fake Out、Fling'], ['Aerodactyl', 'Focus Sash／Unnerve', 'Rock Slide、Dual Wingbeat、Tailwind、Protect'], ['Garchomp', 'White Herb／Rough Skin', 'Stomping Tantrum、Dragon Claw、Swords Dance、Protect']], [90, 145, 145])))
        elif i == 26:
            blocks.append(("text", "仮想ケース：Emboar＋Sinistcha対Mega Charizard Y＋Whimsicott。これは公式記事の役割を練習するための再生で、ダメージ・現行合法性・相手の実際の選出を保証しない。"))
            blocks.append(("table", ([['ターン', '自分の選択', '相手の選択', '読むポイント'], ['1', 'Sinistcha：Rage Powder／Emboar：Bulk Up', 'Whimsicott：Tailwind／Charizard：Protect', '攻撃を受けず、速度の次のターンを買う'], ['2', 'Sinistcha：Trick Room／Emboar：Protect', 'Charizard：Heat Wave／Whimsicott：Encore候補', '起動成功後に主役を守り、残りターンを数える'], ['反証', '起動役が集中される場合', '挑発・集中攻撃・交代', '起動しない選出と代替の速い枠を比較']], [35, 165, 145, 135])))
            blocks.append(("text", "再生後は、Bulk Upの回数ではなく、どの情報で2ターン目のTrick Roomを選んだか、起動役が倒れた場合にどの枠が勝ち筋を引き継ぐかを記録する。"))
        else:
            blocks.append(("lines", ["いま分かっていること", "まだ確認できないこと", "次に行う1時間の実験", "更新・判断への影響"]))
        if 13 <= i <= 15:
            start = (i - 13) * 5
            source_page(canvas, page_number, title, EVIDENCE[start:start + 5], font)
        else:
            page(canvas, page_number, "付録", title, "記録して再利用する", blocks, font, outline=title)
        page_number += 1

    canvas.save()
    return page_number - 1


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/pdf/pokemon-champions-pjcs2027-master-playbook.pdf"))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    validate_source()
    if args.validate_only:
        print(f"source-ok modules={len(MODULES)} weeks={len(WEEKLY_FOCUS)} plans={len(PLANS)} appendix={len(APPENDIX_PAGES)}")
        return 0
    pages = build_pdf(args.output)
    print(f"built {args.output} pages={pages}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
