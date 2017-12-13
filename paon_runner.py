from paon import app, update as update_shows


@app.cli.command()
def update():
    """update shows"""
    update_shows()
