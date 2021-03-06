from flask import abort, render_template, request, redirect, flash, url_for
import datetime
import click
import paon.tmdbwrap as tmdb
from paon import app, db
import paon.utils as utils
from paon.models import Show, Season, Episode


@app.route('/', methods=['GET'])
def get_shows():
    """
    Defines a view that lists all the followed shows, and the episodes that will air in the 7 days to come.
    """
    # return all followed shows
    shows = Show.query.all()
    # return episodes that air during the upcoming week
    today = datetime.datetime.today()
    upcoming = Episode.query.filter(Episode.air_date >= today, Episode.air_date <= today + datetime.timedelta(7)).all()
    return render_template('shows.html', shows=shows, upcoming=upcoming)


@app.route('/shows/<int:show_id>')
def show(show_id):
    """
    Defines a view that displays details for a given show.
    Aborts to a 404 Not Found page if the show doesn't exist.

    :param show_id: the id of the show
    """
    show = Show.query.get(show_id)
    if show is None:
        abort(404)
    return render_template('show.html', show=show)


@app.route('/search/')
def search():
    search_str = request.args.get('search', None)
    results = []
    if search_str:
        s = tmdb.Search()
        results = s.tvshow(search_str)
    return render_template('search.html', shows=results, search=search_str)


@app.route('/add', methods=['GET'])
def add_show():
    # get id and name from request
    tmdb_id = request.args.get('id', None)
    if tmdb_id is None:
        return redirect(url_for('get_shows'))
    elif Show.query.get(tmdb_id) is not None:
        return "Cette série est déjà suivie"
    app.logger.info(f"Getting show {tmdb_id} from tmdb")
    # get show details
    t = tmdb.Tv()
    ts = tmdb.TvSeasons()
    show = t.by_id(tmdb_id)
    if show is None:
        app.logger.warn(f"Got None when searching tmdb for {tmdb_id}")
        flash("Une erreur s'est produite.")
        return redirect(url_for('get_shows'))
    # create show in db
    new_show = Show(
        show['id'],
        show['name'],
        show['number_of_seasons'])
    # fetch seasons
    for season in show['seasons']:
        # avoid season 0 that is usually Specials
        if season['season_number'] == 0:
            continue
        new_season = Season(
            season['id'],
            tmdb_id,
            season['season_number'],
            season['episode_count'],
            utils.tmdb_date_to_date(season['air_date']))
        # get season object
        season_obj = ts.by_id(show['id'], season['season_number'])
        # fetch episodes
        for ep in season_obj['episodes']:
            new_ep = Episode(
                ep['id'],
                tmdb_id,
                season_obj['id'],
                ep['episode_number'],
                utils.tmdb_date_to_date(ep['air_date']))
            new_season.episodes.append(new_ep)
        new_show.seasons.append(new_season)
    db.session.add(new_show)
    db.session.commit()
    app.logger.info(f"Added show {tmdb_id} ({new_show.name}) to database")
    # confirm and redirect user
    flash("Ajout effectué")
    return redirect(url_for('get_shows'))


@app.route('/shows/<int:show_id>/update')
def update_show(show_id):
    # get id and name from request
    show = Show.query.get(show_id)
    ep_id = request.args.get('ep', None)
    if ep_id is None:
        abort(400)
    episode = Episode.query.get(ep_id)
    if show is None or episode is None:
        abort(404)

    # check that episode is part of the show
    if episode.season.show_id != show_id:
        abort(400)

    # mark all episodes from beginning as watched
    mark_as_watched = []
    season_nb = episode.season.number
    if season_nb > 1:
        for s in Season.query.filter(Season.show_id == show_id, Season.number < season_nb).all():
            mark_as_watched.extend(s.episodes)
    for ep_current_season in [e for e in episode.season.episodes if e.number <= episode.number]:
        ep_current_season.watched = True
    for e in mark_as_watched:
        e.watched = True

    db.session.commit()
    return redirect(url_for('show', show_id=show_id))


@app.route('/shows/<int:show_id>/reset')
def reset_show(show_id):
    """
    Mark all episodes as not watched
    :param show_id:
    """
    show = Show.query.get(show_id)
    if show is None:
        app.logger.error(f"Didn't find show with id {show_id} in database.")
        abort(404)
    for episode in show.episodes:
        episode.watched = False

    db.session.commit()
    return redirect(url_for('show', show_id=show_id))


@app.route('/shows/<int:show_id>/remove')
def remove_show(show_id):
    if not _do_remove(show_id):
        flash("Une erreur s'est produite.")
    return redirect(url_for('get_shows'))


@app.cli.command()
@click.argument("show_id", type=click.INT)
def remove_cmd(show_id):
    _do_remove(show_id)


def _do_remove(show_id):
    """
    Delete a show from the database.
    The deletion process will also delete related seasons and episodes.
    """
    show = Show.query.get(show_id)
    if show is None:
        app.logger.error(f"Didn't find show with id {show_id} in database.")
        return False
    app.logger.info(f"deleting {show.name}")
    db.session.delete(show)
    db.session.commit()
    return True


@app.cli.command()
def update():
    myshows = Show.query.all()
    t = tmdb.Tv()
    ts = tmdb.TvSeasons()
    for myshow in myshows:
        show = t.by_id(myshow.tmdb_id)
        last_aired_date = utils.tmdb_date_to_date(show['last_air_date'])
        last_local_episode = Episode.query.filter(
            Episode.show_id == myshow.tmdb_id
        ).order_by(Episode.air_date.desc()).first()
        app.logger.info(f"{myshow.name}: local: {last_local_episode.air_date}, most recent: {last_aired_date}")
        if last_aired_date > last_local_episode.air_date:
            app.logger.info(f"{myshow.name} needs an update")
            # get last season
            mylastseason = myshow.get_season(myshow.season_count)
            lastseason = ts.by_id(myshow.tmdb_id, myshow.season_count)
            missing_count = len(lastseason['episodes']) - mylastseason.episode_count
            for i in range(mylastseason.episode_count, mylastseason.episode_count + missing_count):
                ep = lastseason['episodes'][i]
                new_ep = Episode(
                    ep['id'],
                    myshow.tmdb_id,
                    lastseason['id'],
                    ep['episode_number'],
                    utils.tmdb_date_to_date(ep['air_date']))
                mylastseason.episodes.append(new_ep)

            mylastseason.episode_count = len(mylastseason.episodes)

            # are we also missing seasons ?
            seasons_diff = show['number_of_seasons'] - myshow.season_count
            if seasons_diff > 0:
                for new_s in show['seasons']:
                    if new_s['season_number'] <= mylastseason.number:
                        continue
                    new_season = Season(
                        new_s['id'],
                        myshow.tmdb_id,
                        new_s['season_number'],
                        new_s['episode_count'],
                        utils.tmdb_date_to_date(new_s['air_date']))
                    # get season object
                    season_obj = ts.by_id(myshow.tmdb_id, new_s['season_number'])
                    # fetch episodes
                    for ep in season_obj['episodes']:
                        new_ep = Episode(
                            ep['id'],
                            myshow.tmdb_id,
                            season_obj['id'],
                            ep['episode_number'],
                            utils.tmdb_date_to_date(ep['air_date']))
                        new_season.episodes.append(new_ep)
                    myshow.seasons.append(new_season)
                    myshow.season_count = len(myshow.seasons)

            db.session.commit()
            app.logger.info(f"{myshow.name} is up to date")
