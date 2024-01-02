import os
import itertools
from flask import Flask, render_template, send_from_directory, make_response, request
from util import Dict2Class, connect, nbsp_names, hcp, vp
from urllib.parse import urlparse

VULNERABILITY = ["e",
                 "-", "n", "e", "b",
                 "n", "e", "b", "-",
                 "e", "b", "-", "n",
                 "b", "-", "n"]
SUITS = "shdc"
hands = "nesw"
DENOMINATIONS = "cdhsn"

app = Flask(__name__)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/sitemap")
@app.route("/sitemap/")
@app.route("/sitemap.xml")
def sitemap():
    """
        Route to dynamically generate a sitemap of your website/application.
        lastmod and priority tags omitted on static pages.
        lastmod included on dynamic content such as blog posts.
    """

    host_components = urlparse(request.host_url)
    host_base = host_components.scheme + "://" + host_components.netloc

    # Static routes with static content
    static_urls = list()
    for rule in app.url_map.iter_rules():
        if not str(rule).startswith("/admin") and not str(rule).startswith("/user"):
            if "GET" in rule.methods and len(rule.arguments) == 0:
                url = {
                    "loc": f"{host_base}{str(rule)}"
                }
                static_urls.append(url)

    # Dynamic routes with dynamic content
    dynamic_urls = list()
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select tournament_id,boards,players from tournaments order by date desc')
    data = cursor.fetchall()
    conn.close()
    for (tournament_id, boards, players) in data:
        dynamic_urls.append({"loc": f"{host_base}/result/{tournament_id}/ranks"})
        dynamic_urls.extend(({'loc': f'{host_base}/result/{tournament_id}/scorecard/{i}'}
                             for i in range(1, players + 1)))
        dynamic_urls.extend(({'loc': f'{host_base}/result/{tournament_id}/board/{i}'}
                             for i in range(1, boards + 1)))

    xml_sitemap = render_template("sitemap.xml", static_urls=static_urls, dynamic_urls=dynamic_urls,
                                  host_base=host_base)
    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"

    return response


@app.route('/')
def home():
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f"""select value from strings where "key"='home'""")
        home_page_html = cursor.fetchone()[0]
        page = render_template('home.html', homepage_html=home_page_html)
    except:
        page = render_template('home.html')
    finally:
        conn.close()

    return page


@app.route('/contest')
def contest():
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f'''
with results as (
    select trim(unnest(string_to_array(partnership, ' & '))) player, masterpoints  from names  
	left join tournaments  on names.tournament_id = tournaments.tournament_id
    where masterpoints > 0 and names.tournament_id > 0 and "date" >= '2023-10-08'::date
), all_results as (select * from results union all select player, masterpoints from matches where "date" >= '2023-10-08'::date)
SELECT
	player,
	SUM (masterpoints) total
FROM
	all_results left join players on trim(players.full_name) = all_results.player
	where players."rank" < 18
GROUP BY
	player
order by total desc''')
        data = cursor.fetchall()
    finally:
        conn.close()
    contestants = [Dict2Class({'name': d[0], 'masterpoints': d[1]}) for d in data]
    return render_template('contest.html', contestants=contestants)


@app.route('/tournaments')
def tournaments():
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f'select tournament_id,date,scoring,players  from tournaments order by date desc')
        data = cursor.fetchall()
        cursor.execute("""select tournament_id,"number",partnership from names where "rank"='1' or "rank" like '1−%'""")
        winners = cursor.fetchall()
    finally:
        conn.close()
    tournaments_list = []
    for d in data:
        winner = [w for w in winners if w[0] == d[0]][0]
        tournaments_list.append(Dict2Class({
            'id': d[0], 'date': d[1], 'scoring': d[2], 'players': d[3], 'winner_num': winner[1],
            'winner_names': winner[2]
        }))
    return render_template('tournaments.html', tournaments=tournaments_list)


@app.route('/pairs')
def pairs():
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f"""select 
        array_to_string((select array (select trim(unnest(string_to_array(partnership, ' & '))) as a order by a)), ' & ') p, 
        avg(percent) avg_percent, count(*) played, 
        count(case left(rank, 2) when '1−' then 1 when '1' then 1 else null end) wins 
        from names where tournament_id > 0 group by p order by wins desc, avg_percent desc""")
        data = cursor.fetchall()
    finally:
        conn.close()
    return render_template('pairs.html', pairs=[Dict2Class(
        {'names': d[0], 'played': d[2], 'avg': round(d[1], 2), 'wins': d[3]}) for d in data])


@app.route('/rating')
def rating():
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f'select id,full_name,rating,rank,rank_ru,last_year from players order by rating desc')
        data = cursor.fetchall()
    finally:
        conn.close()
    return render_template('rating.html', players=[Dict2Class(
        {'id': d[0], 'name': d[1], 'rating': d[2], 'rank': d[3], 'rank_ru': "" if d[4] == 1.6 else d[4],
         'last_year': d[5] or ''}) for d in data])


@app.route('/personal/<player_id>')
def personal(player_id):
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f'select full_name from players where id={player_id}')
        player_name = cursor.fetchone()[0].strip()
        cursor.execute(f'''WITH results AS
(
    select trim(unnest(string_to_array(partnership, ' & '))) player, partnership , masterpoints, "rank", names.tournament_id, 
    "date"  from names  left join tournaments  on names.tournament_id = tournaments.tournament_id 
    where masterpoints > 0 and names.tournament_id > 0
)
select results.masterpoints, results.tournament_id, results."date", results."rank", 
    replace(replace(results.partnership, '{player_name} & ', ''), ' & {player_name}', '') partner from results 
where player = '{player_name}' order by tournament_id DESC''')
        data = cursor.fetchall()
        cursor.execute(f"""select masterpoints, NULL, "date", NULL, NULL from matches where player='{player_name}'""")
        match_results = cursor.fetchall()
        all_results = list(reversed(sorted(data + match_results, key=lambda x:x[2])))
    finally:
        conn.close()
    return render_template('personal.html', name=player_name, results=[Dict2Class({
        'masterpoints': d[0], 'tournament_id': d[1], "date": d[2], "rank": d[3], "partner": d[4]}) for d in all_results])


@app.route('/result/<tournament_id>/ranks')
def ranks(tournament_id):
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
        data = cursor.fetchone()
        cursor.execute(f"select * from names where tournament_id={tournament_id} order by regexp_replace(rank, '[-−−–].*', '', 'g')::int")
        totals = [list(c) for c in cursor.fetchall()]
        if data[4] == 'Swiss IMPs':
            cursor.execute(f'select ns, ew, mp_ns, mp_ew from protocols where tournament_id={tournament_id} order by number')
            protocols = cursor.fetchall()
            for t in totals:
                t[5] = 0
                for p in protocols:
                    t[5] += p[2] * (p[0] == t[1]) + p[3] * (p[1] == t[1])

    finally:
        conn.close()

    totals_dict = [Dict2Class({"rank": total[3], "number": total[1], "names": nbsp_names(total[2]), "mp": total[5],
                               "vp": total[4],
                               "percent": total[5], "masterpoints": total[6] or '', "masterpoints_ru": total[7] or ''})
                   for total in totals]
    return render_template('rankings_template_web.html', scoring= data[4], max=data[3], tables=data[2] // 2,
                           date=data[0], boards=data[1], tournament_title=data[6], totals=totals_dict,
                           tournament_id=tournament_id)


@app.route('/result/<tournament_id>/scorecard/<pair_number>')
def scorecard(tournament_id, pair_number):
    tournament_id = int(tournament_id)
    pair_number = int(pair_number)
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f"select distinct number from boards where tournament_id={tournament_id}")
        played_boards = set(b[0] for b in cursor.fetchall())
        cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
        data = cursor.fetchone()
        cursor.execute(f'select number, partnership, rank, mps, percent from names where tournament_id={tournament_id}')
        names = cursor.fetchall()
        pair_results = [n for n in names if n[0] == pair_number][0]
        cursor.execute(f'select * from protocols where tournament_id={tournament_id} and (ew={pair_number} or ns={pair_number}) order by number')
        personals = cursor.fetchall()
    finally:
        conn.close()
    max_mp = (data[2] // 2 - 1) * 2
    scoring_short = data[4].rstrip("s").replace("Cross-", "X").replace('Swiss ', '')
    pair = Dict2Class({"name": nbsp_names(pair_results[1]), "number": pair_number,
                       "mp_total": 0,
                       "vp_total": pair_results[3],
                       "percent_total": pair_results[4],
                       "rank": pair_results[2], "boards": []})

    vul = {'-': "−", "n": "NS", "e": "EW", "b": "ALL"}
    total_mps = 0
    opps = []
    for b in played_boards:
        result = [p for p in personals if p[1] == b]
        opps.append([result[0][2] + result[0][3] - pair_number if result else None])
    boards_per_round_candidates = [sum(1 for _ in group) for _, group in itertools.groupby(opps)]
    if data[4] == 'Swiss IMPs':
        boards_per_round_candidates = [min(boards_per_round_candidates)] \
                                      * (len(played_boards) // min(boards_per_round_candidates))
    round_sums = [sum(boards_per_round_candidates[:i]) for i in range(len(boards_per_round_candidates))]
    round_sums.extend([data[1], data[1] * 2 - round_sums[-1]])
    for i in range(1, max(played_boards) + 1):
        if i not in played_boards:
            continue
        board_index = len(pair.boards)
        p = [pers for pers in personals if pers[1] == i]
        round_index, right_margin = [(i, round_sum) for i, round_sum in enumerate(round_sums)
                                     if round_sum > board_index][0]
        left_margin = round_sums[round_index - 1]
        boards_per_round = right_margin - left_margin if board_index == left_margin else 1
        if i in played_boards and not p:
            # not played
            pair.boards.append(Dict2Class({"number": i, "vul": vul[VULNERABILITY[i % 16]],
                                           "dir": "", "contract": "NOT&nbsp;PLAYED",
                                           "declarer": "", "lead": "",
                                           "score": '', "mp": 0,
                                           "percent": 0,
                                           "mp_per_round": 0,
                                           "opp_names": "BYE",
                                           "boards_per_round": boards_per_round}))
            continue
        p = p[0]
        position = "NS" if p[2] == pair_number else 'EW'
        index = 8 + (position == 'EW')
        opps = p[2 + (position != 'EW')]
        opp_names = nbsp_names([n for n in names if n[0] == opps][0][1])
        mp = p[index] or 0
        number_diff = i - 1 - board_index
        pair.mp_total += mp
        mp_for_round = sum(res[index] for res in personals
                           if left_margin < res[1] - number_diff <= right_margin)
        vp_for_round = vp(mp_for_round, boards_per_round)


        pair.boards.append(Dict2Class({"number": i, "vul": vul[VULNERABILITY[i % 16]],
                                       "dir": position, "contract": p[4],
                                       "declarer": p[5], "lead": p[6],
                                       "score": p[7] if p[7] != 1 else '', "mp": mp,
                                       "percent": round(mp/max_mp, 2),
                                       "mp_per_round": round(mp_for_round, 2),
                                       "vp": round(vp_for_round, 2),
                                       "opp_names": opp_names,
                                       "boards_per_round": boards_per_round}))
        total_mps += mp
    if pair.mp_total < total_mps - 0.5:  # rounding error
        pair.penalties = pair.mp_total - total_mps
    return render_template('scorecards_template_web.html', scoring_short=scoring_short, max_mp=data[3],
                           pair=pair, tournament_id=tournament_id, scoring=data[4])


@app.route('/result/<tournament_id>/board/<board_number>')
def board(tournament_id, board_number):
    tournament_id = int(tournament_id)
    board_number = int(board_number)
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f"select distinct number from boards where tournament_id={tournament_id} order by number")
        played_boards = [b[0] for b in cursor.fetchall()]
        cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
        data = cursor.fetchone()
        cursor.execute(f'select number, partnership from names where tournament_id={tournament_id}')
        names = cursor.fetchall()
        cursor.execute(f'select * from protocols where tournament_id={tournament_id} and number={board_number} order by mp_ns desc')
        personals = cursor.fetchall()

        cursor.execute(f'select * from boards where tournament_id={tournament_id} and number={board_number}')
        board_data = cursor.fetchone()

    finally:
        conn.close()
    scoring_short = data[4].rstrip("s").replace("Cross-", "X").replace('Swiss ', '')
    vul = {'-': "−", "n": "NS", "e": "EW", "b": "ALL"}

    repl_dict = {"d": hands[(board_number - 1) % 4].upper(), "b": board_number,
                 "v": vul[VULNERABILITY[board_number % 16]],
                 "minimax_contract": board_data[38], "minimax_outcome": board_data[39], "minimax_url": board_data[40],
                 "played_boards": played_boards}
    for i, h in enumerate(hands):
        for j, s in enumerate(SUITS):
            repl_dict[f"{h}{s}"] = board_data[2 + i * 4 + j].upper().replace("T", "10")
        for j, d in enumerate(reversed(DENOMINATIONS)):
            repl_dict[f"{h}_par_{d}"] = board_data[18+i*5+j]
    repl_dict['n_hcp'] = hcp(''.join(board_data[2:6]))
    repl_dict['e_hcp'] = hcp(''.join(board_data[6:10]))
    repl_dict['s_hcp'] = hcp(''.join(board_data[10:14]))
    repl_dict['w_hcp'] = 40 - repl_dict['n_hcp'] - repl_dict['e_hcp'] - repl_dict['s_hcp']
    dealer_low = repl_dict["d"].lower()
    repl_dict["ns_vul"] = (repl_dict["v"] in ("EW", "−")) * "non" + "vul"
    repl_dict["ew_vul"] = (repl_dict["v"] in ("NS", "−")) * "non" + "vul"
    repl_dict[f"{dealer_low}_dealer"] = "dealer"
    repl_dict["tables"] = []

    current_board = Dict2Class(repl_dict)
    for p in personals:
        repl_dict = {"ns": p[2], "ew": p[3], "contract": p[4], "declarer": p[5], "lead": p[6],
                     "nsplus": p[7] if p[7] > 1 else "", "nsminus": -p[7] if p[7] < 0 else "", "mp_ns": round(p[8], 2),
                     "mp_ew": round(p[9], 2), "ns_name": nbsp_names([n[1] for n in names if n[0] == p[2]][0]),
                     "ew_name": nbsp_names([n[1] for n in names if n[0] == p[3]][0]), "bbo_url": p[10]}
        current_board.tables.append(Dict2Class(repl_dict))

    return render_template('travellers_template_web.html', scoring_short=scoring_short, board=current_board,
                           tournament_id=tournament_id, maxboard=data[1])
