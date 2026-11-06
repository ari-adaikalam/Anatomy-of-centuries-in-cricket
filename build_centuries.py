"""Builds the tables in data/ that the notebook reads, from the ball-by-ball dataset.

Usage:  python build_centuries.py --data <folder holding ball_by_ball_data.csv, matches.csv, innings.csv and players.csv> [--out data]

The dataset is The Ultimate Ball-by-Ball Cricket Dataset (https://github.com/ari-adaikalam/The-Ultimate-Ball-by-Ball-Cricket-Dataset), built from Cricsheet (https://cricsheet.org, ODC-BY).

centuries.csv: one row for every innings of 100 or more. A century is a batter's total of 100 or more runs off the bat in one innings of one match. Super Over innings are left out.
  balls                   deliveries faced: every ball except a wide (a no-ball counts)
  balls_to_50, _to_100    the ball, counted in balls faced, on which the batter passed 50 and 100
  position                order of arrival at the crease, the opening pair being 1 and 2
  fours, sixes            boundaries hit off the bat (an overthrow four is not counted)
  not_out                 the batter was still in when the innings ended
  chasing                 the innings had a target, or was the fourth innings of a Test
  result                  won, lost, tied, draw or no result, for the batter's team

Three smaller tables give the context the charts compare against:
  player_format.csv   for each player and format: innings batted, scores of 50 to 99 (fifties) and of 100 or more (hundreds)
  team_innings.csv    for each format and for batting first or chasing: team innings, and how many held a century
  team_results.csv    for each format: how every team's matches ended, whatever the batting
"""
import argparse
from pathlib import Path
import duckdb


def build(data: Path, out: Path) -> dict[str, int]:
    con = duckdb.connect()
    ball = data / "ball_by_ball_data.csv"
    matches, innings_file, players = data / "matches.csv", data / "innings.csv", data / "players.csv"
    con.execute(f"""
        create temp table d as
        select match_id, innings, delivery_number, striker_id, striker, non_striker, runs_off_bat,
               coalesce(wides, 0) as wides, coalesce(non_boundary, false) as non_boundary,
               player_dismissed, wicket_type, batting_team, bowling_team
        from read_csv('{ball}', header = true, sample_size = 200000)
    """)
    # Every normal innings, with its format and whether it was a chase. The data holds a target only for limited-overs
    # innings, so the fourth innings of a Test is counted as the chase.
    con.execute(f"""
        create temp table inn as
        select i.match_id, i.innings, i.batting_team as team, m."format" as format,
               i.target_runs is not null or (m."format" = 'TEST' and i.innings = 4) as chasing
        from read_csv('{innings_file}', header = true) i
        join read_csv('{matches}', header = true) m using (match_id)
        where not coalesce(i.is_super_over, false)
    """)
    # One row for each batter in each innings, with every score, the centuries and the rest.
    con.execute("""
        create temp table a as
        select d.match_id, d.innings, d.striker_id as player_id, any_value(d.striker) as batter,
               any_value(d.batting_team) as team, any_value(d.bowling_team) as opponent,
               sum(d.runs_off_bat) as runs,
               count(*) filter (where d.wides = 0) as balls,
               count(*) filter (where d.runs_off_bat = 4 and not d.non_boundary) as fours,
               count(*) filter (where d.runs_off_bat = 6 and not d.non_boundary) as sixes,
               bool_or(coalesce(d.player_dismissed = d.striker and d.wicket_type not in ('retired hurt', 'retired not out'), false)) as dismissed
        from d join inn using (match_id, innings)
        where d.striker_id is not null
        group by 1, 2, 3
    """)
    con.execute("create temp table s as select * from a where runs >= 100")
    # The ball, counted in balls faced, on which each century passed 50 and 100.
    con.execute("""
        create temp table pace as
        select match_id, innings, player_id,
               min(faced) filter (where cum >= 50) as balls_to_50,
               min(faced) filter (where cum >= 100) as balls_to_100
        from (select d.match_id, d.innings, d.striker_id as player_id,
                     sum(d.runs_off_bat) over w as cum,
                     count(*) filter (where d.wides = 0) over w as faced
              from d join s on s.match_id = d.match_id and s.innings = d.innings and s.player_id = d.striker_id
              window w as (partition by d.match_id, d.innings, d.striker_id order by d.delivery_number))
        group by 1, 2, 3
    """)
    # Arrival order: the first ball on which a name appears, as striker or non-striker.
    con.execute("""
        create temp table arrival as
        select match_id, innings, name, row_number() over (partition by match_id, innings order by first_ball, name) as position
        from (select match_id, innings, name, min(delivery_number) as first_ball
              from (select match_id, innings, striker as name, delivery_number from d
                    union all select match_id, innings, non_striker as name, delivery_number from d)
              group by 1, 2, 3)
    """)
    con.execute(f"""
        create temp table centuries as
        select p.name as player, s.player_id, p.gender, m.start_date as date, year(m.start_date) as year,
               m."format" as format, m."type" as competition_type, m.event, m.venue, s.team, s.opponent,
               s.match_id, s.innings as match_innings, a.position,
               s.runs, s.balls, round(100.0 * s.runs / s.balls, 1) as strike_rate,
               pace.balls_to_50, pace.balls_to_100, s.fours, s.sixes,
               not s.dismissed as not_out, inn.chasing,
               case when m.outcome = 'draw' then 'draw'
                    when m.outcome = 'tie' then 'tied'
                    when m.winner is null then 'no result'
                    when m.winner = s.team then 'won' else 'lost' end as result
        from s
        join inn using (match_id, innings)
        join pace using (match_id, innings, player_id)
        join read_csv('{matches}', header = true) m using (match_id)
        join read_csv('{players}', header = true) p on p.player_id = s.player_id
        left join arrival a on a.match_id = s.match_id and a.innings = s.innings and a.name = s.batter
        order by m.start_date, s.match_id, s.innings, a.position
    """)
    con.execute(f"""
        create temp table player_format as
        select p.name as player, a.player_id, p.gender, inn.format,
               count(*) as innings,
               count(*) filter (where a.runs >= 50 and a.runs < 100) as fifties,
               count(*) filter (where a.runs >= 100) as hundreds
        from a join inn using (match_id, innings)
        join read_csv('{players}', header = true) p on p.player_id = a.player_id
        group by 1, 2, 3, 4
        having count(*) filter (where a.runs >= 50) > 0
        order by hundreds desc, fifties desc
    """)
    con.execute("""
        create temp table team_innings as
        select inn.format, inn.chasing, count(*) as team_innings,
               count(*) filter (where exists (select 1 from s where s.match_id = inn.match_id and s.innings = inn.innings)) as with_a_century
        from inn group by 1, 2 order by 1, 2
    """)
    con.execute(f"""
        create temp table team_results as
        select m."format" as format,
               case when m.outcome = 'draw' then 'draw' when m.outcome = 'tie' then 'tied'
                    when m.winner is null then 'no result' when m.winner = t.team then 'won' else 'lost' end as result,
               count(*) as team_matches
        from read_csv('{matches}', header = true) m
        cross join lateral (select unnest([m.team_1, m.team_2]) as team) t
        where m.match_id in (select match_id from inn)
        group by 1, 2 order by 1, 2
    """)
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name in ("centuries", "player_format", "team_innings", "team_results"):
        con.execute(f"copy {name} to '{out / (name + '.csv')}' (header, delimiter ',')")
        counts[name] = con.execute(f"select count(*) from {name}").fetchone()[0]
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("data"))
    args = ap.parse_args()
    for name, n in build(args.data, args.out).items():
        print(f"{name}.csv: {n:,} rows")
