# coding: utf-8

try:
    import urllib.request as urlrequest
except ImportError:
    import urllib as urlrequest

from datetime import datetime, timedelta
import json
import urllib


class Team(object):
    def __init__(self, header, line):
        tokens_header = header.split('-')
        tokens_line = line.split('-')
        self.names = {}
        for i, h in enumerate(tokens_header):
            self.names[h] = tokens_line[i].decode('utf-8')

    def match(self, arg):
        for name in self.names.values():
            if name.lower().find(arg.lower()) >= 0:
                return True
        return False

    def get_name(self, h):
        return self.names.get(h, '')

    def get_icon(self):
        return "team-icons/" + self.get_name('ena') + ".png"


class NBA(object):
    def __init__(self):
        self.teams = self.load_teams()

    def search(self, arg):
        if arg == 'now':
            games = self.get_recent_games()
            return json.dumps({
                "items": self.get_now_playing_game(None, games)
            })
        elif arg == 'up':
            games = self.get_recent_games()
            return json.dumps({
                "items": self.get_upcoming_games(None, games)
            })
        elif arg == 'past':
            games = self.get_recent_games()
            return json.dumps({
                "items": self.get_past_games(None, games)
            })
        elif arg.startswith('tod'):
            return json.dumps({
                "items": self.get_today_games()
            })
        teams = self.pick_team(arg)
        if len(teams) > 1:
            r = []
            for team in teams:
                t = {
                    "autocomplete": team.get_name('ena'),
                    "valid": False,
                    "title": team.get_name('en'),
                    "subtitle": u"选择 " + team.get_name('zh'),
                    "icon": {
                        "path": team.get_icon(),
                    }
                }
                r.append(t)
            return json.dumps({"items": r})
        else:
            team = teams[0]
            games = self.get_recent_games()
            return json.dumps({
                "items": self.get_now_playing_game(team, games) + self.get_upcoming_games(team, games) + self.get_past_games(team, games)
            })

    def search_past_games(self, arg):
        teams = self.pick_team(arg)
        if len(teams) > 1:
            r = []
            for team in teams:
                t = {
                    "autocomplete": team.get_name('ena'),
                    "valid": False,
                    "title": team.get_name('en'),
                    "subtitle": u"选择 " + team.get_name('zh'),
                    "icon": {
                        "path": team.get_icon(),
                    }
                }
                r.append(t)
            return json.dumps({"items": r})
        else:
            team = teams[0]
            games = self.get_recent_games()
            return json.dumps({
                "items": self.get_past_games(team, games, True)
            })

    def get_recent_games(self):
        today = datetime.now()
        start = today + timedelta(days=-90)
        end = today + timedelta(days=90)
        url = 'http://matchweb.sports.qq.com/kbs/list?columnId=100000&startTime=%s&endTime=%s&_=1483724931822' % (
            start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        return json.loads(urlrequest.urlopen(url).read().decode('utf-8'))['data']

    def get_today_games(self):
        r = []
        today = datetime.now().strftime('%Y-%m-%d')
        url = 'http://matchweb.sports.qq.com/kbs/list?columnId=100000&startTime=%s&endTime=%s&_=1483724931822' % (
            today, today)
        games = json.loads(urlrequest.urlopen(
            url).read().decode('utf-8'))['data']
        if today not in games:
            return []
        for game in games[today]:
            g = self.get_base_game(team, game)
            g['subtitle'] = game['matchDesc'] + \
                " " + u'开始于 ' + game['startTime']
            r.append(g)
        return r

    def get_now_playing_game(self, team, games):
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in games:
            return []
        r = []
        for game in games[today]:
            if ((team is not None and self.match_game(team, game)) or (team is None)) and game['matchPeriod'] == '1':
                g = self.get_base_game(team, game)
                g['subtitle'] = game['matchDesc'] + u" 正在进行 " + \
                    game['quarter'] + " " + game['quarterTime']
                r.append(g)
        return rw

    def get_upcoming_games(self, team, games):
        matched_games = []
        today = datetime.now().strftime('%Y-%m-%d')
        for day, gs in games.items():
            if day >= today:
                for game in gs:
                    if self.match_game(team, game) and game['matchPeriod'] == '0':
                        matched_games.append(game)
        matched_games.sort(key=lambda x: x['startTime'], reverse=False)
        matched_games = matched_games[0:10]
        ret_games = []
        for game in matched_games:
            g = self.get_base_game(team, game)
            g['subtitle'] = game['matchDesc'] + " " + \
                u'将在 ' + game['startTime'] + u' 开始'
            ret_games.append(g)
        return ret_games

    def get_team(self, name, h='zha'):
        for team in self.teams:
            if team.get_name(h) == name:
                return team

    def get_base_game(self, team, game, without_score=False):
        if team is None:
            team = self.get_team(game['leftName'])
        g = {}
        away = True
        other_team = None
        my_goal = None
        other_goal = None
        if game['leftName'] != team.get_name('zha'):
            away = False
            other_team = self.get_team(game['leftName'])
            other_goal = game['leftGoal']
            my_goal = game['rightGoal']
        else:
            away = True
            other_team = self.get_team(game['rightName'])
            other_goal = game['rightGoal']
            my_goal = game['leftGoal']
        g['title'] = team.get_name('ena') + " " + my_goal + " " + (
            "@" if away else "vs") + " " + other_goal + " " + other_team.get_name('ena')
        if without_score:
            g['title'] = team.get_name(
                'ena') + " " + ("@" if away else "vs") + " " + other_team.get_name('ena')
        g['icon'] = {'path': other_team.get_icon()}
        g['arg'] = 'http://sports.qq.com/kbsweb/game.htm?mid=%s' % (
            game['mid'])
        return g

    def get_past_games(self, team, games, without_score=False):
        matched_games = []
        today = datetime.now().strftime('%Y-%m-%d')
        for day, gs in games.items():
            if day <= today:
                for game in gs:
                    if self.match_game(team, game) and game['matchPeriod'] == '2':
                        matched_games.append(game)

        matched_games.sort(key=lambda x: x['startTime'], reverse=True)
        ret_games = []
        for game in matched_games:
            g = self.get_base_game(team, game, without_score)
            g['subtitle'] = game['matchDesc'] + " " + \
                u'结束于 ' + game['startTime'].split()[0]
            ret_games.append(g)
        return ret_games

    def match_game(self, team, game):
        if game['matchType'] != '2':
            return False
        if not team:
            return True
        zh_name_abbr = team.get_name('zha')
        if game['leftName'] == zh_name_abbr or game['rightName'] == zh_name_abbr:
            return True
        return False

    def load_teams(self):
        teams = []
        with open("./teams") as f:
            lines = f.read().strip().split('\n')
            for line in lines[1:]:
                teams.append(Team(lines[0], line))
        return teams

    def pick_team(self, arg):
        if len(arg) == 3 and arg.isupper():
            for team in self.teams:
                if team.get_name('ena') == arg:
                    return [team]
        teams = []
        for team in self.teams:
            if team.match(arg):
                teams.append(team)
        return teams
