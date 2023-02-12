import os
from flask import Flask, render_template, send_from_directory
from util import Dict2Class, connect, nbsp_names, hcp

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


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/tournaments')
def tournaments():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select tournament_id,date,scoring,players  from tournaments order by date desc')
    data = cursor.fetchall()

    cursor.execute("""select tournament_id,"number",partnership from names where "rank"='1' or "rank" like '1−%'""")
    winners = cursor.fetchall()
    tournaments_list = []
    for d in data:
        winner = [w for w in winners if w[0] == d[0]][0]
        tournaments_list.append(Dict2Class({
            'id': d[0], 'date': d[1], 'scoring': d[2], 'players': d[3], 'winner_num': winner[1],
            'winner_names': winner[2]
        }))
    conn.close()
    return render_template('tournaments.html', tournaments=tournaments_list)


@app.route('/pairs')
def pairs():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f"""select 
    array_to_string((select array (select trim(unnest(string_to_array(partnership, ' & '))) as a order by a)), ' & ') p, 
    avg(percent) avg_percent, count(*) played, 
    count(case left(rank, 2) when '1−' then 1 when '1' then 1 else null end) wins 
    from names group by p order by wins desc""")
    data = cursor.fetchall()
    return render_template('pairs.html', pairs=[Dict2Class(
        {'names': d[0], 'played': d[2], 'avg': round(d[1], 2), 'wins': d[3]}) for d in data])


@app.route('/rating')
def rating():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select full_name,rating,rank,rank_ru,last_year  from players order by rating desc')
    data = cursor.fetchall()

    conn.close()
    return render_template('rating.html', players=[Dict2Class(
        {'name': d[0], 'rating': d[1], 'rank': d[2], 'rank_ru': "" if d[3] == 1.6 else d[3],
         'last_year': d[4] or ''}) for d in data])


@app.route('/result/<tournament_id>/ranks')
def ranks(tournament_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f"select * from names where tournament_id={tournament_id} order by regexp_replace(rank, '−.*', '', 'g')::int")
    totals = cursor.fetchall()
    totals_dict = [Dict2Class({"rank": total[3], "number": total[1], "names": nbsp_names(total[2]), "mp": total[4],
                               "percent": total[5], "masterpoints": total[6] or '', "masterpoints_ru": total[7] or ''})
                   for total in totals]
    conn.close()
    return render_template('rankings_template_web.html', scoring= data[4], max=data[3], tables=data[2] // 2,
                           date=data[0], boards=data[1], tournament_title=data[6], totals=totals_dict,
                           tournament_id=tournament_id)


@app.route('/result/<tournament_id>/scorecard/<pair_number>')
def scorecard(tournament_id, pair_number):
    tournament_id = int(tournament_id)
    pair_number = int(pair_number)
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select number, partnership, rank, mps, percent from names where tournament_id={tournament_id}')
    names = cursor.fetchall()
    pair_results = [n for n in names if n[0] == pair_number][0]
    cursor.execute(f'select * from protocols where tournament_id={tournament_id} and (ew={pair_number} or ns={pair_number}) order by number')
    personals = cursor.fetchall()
    max_mp = (data[2] // 2 - 1) * 2
    scoring_short = data[4].rstrip("s").replace("Cross-", "X")
    pair = Dict2Class({"name": nbsp_names(pair_results[1]), "number": pair_number, "scoring": data[4],
                       "mp_total": pair_results[3],
                       "percent_total": pair_results[4],
                       "rank": pair_results[2], "boards": []})

    boards_per_round = data[1] // data[-1]
    vul = {'-': "−", "n": "NS", "e": "EW", "b": "ALL"}
    for i in range(1, data[1] + 1):
        p = [pers for pers in personals if pers[1] == i]
        if not p:
            # not played
            pair.boards.append(Dict2Class({"number": i, "vul": vul[VULNERABILITY[i % 16]],
                                               "dir": "", "contract": "NOT&nbsp;PLAYED",
                                               "declarer": "", "lead": "",
                                               "score": '', "mp": 0,
                                               "percent": 0,
                                               "mp_per_round": 0,
                                               "opp_names": "BYE"}))
            continue
        p = p[0]
        position = "NS" if p[2] == pair_number else 'EW'
        index = 8 + (position == 'EW')
        opps = p[2 + (position != 'EW')]
        opp_names = nbsp_names([n for n in names if n[0] == opps][0][1])
        mp = p[index] or 0
        current_round = (i - 1) // boards_per_round

        mp_for_round = sum(res[index] for res in personals
                           if current_round * boards_per_round < res[1] <= (current_round + 1) * boards_per_round)

        pair.boards.append(Dict2Class({"number": i, "vul": vul[VULNERABILITY[i % 16]],
                                       "dir": position, "contract": p[4],
                                       "declarer": p[5], "lead": p[6],
                                       "score": p[7] if p[7] != 1 else '', "mp": mp,
                                       "percent": round(mp/max_mp, 2),
                                       "mp_per_round": round(mp_for_round, 2),
                                       "opp_names": opp_names}))
    conn.close()
    return render_template('scorecards_template_web.html', scoring_short=scoring_short, max_mp=data[3],
                           boards_per_round=boards_per_round, pair=pair, tournament_id=tournament_id)


@app.route('/result/<tournament_id>/board/<board_number>')
def board(tournament_id, board_number):
    tournament_id = int(tournament_id)
    board_number = int(board_number)
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(f'select * from tournaments where tournament_id={tournament_id}')
    data = cursor.fetchone()
    cursor.execute(f'select number, partnership from names where tournament_id={tournament_id}')
    names = cursor.fetchall()
    cursor.execute(f'select * from protocols where tournament_id={tournament_id} and number={board_number} order by mp_ns desc')
    personals = cursor.fetchall()

    cursor.execute(f'select * from boards where tournament_id={tournament_id} and number={board_number}')
    board_data = cursor.fetchone()
    scoring_short = data[4].rstrip("s").replace("Cross-", "X")
    vul = {'-': "−", "n": "NS", "e": "EW", "b": "ALL"}

    repl_dict = {"d": hands[(board_number - 1) % 4].upper(), "b": board_number, "v": vul[VULNERABILITY[board_number % 16]],
                 "minimax_contract": board_data[38], "minimax_outcome": board_data[39], "minimax_url": board_data[40]}
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

    conn.close()
    return render_template('travellers_template_web.html', scoring_short=scoring_short, board=current_board,
                           tournament_id=tournament_id, maxboard=data[1])


