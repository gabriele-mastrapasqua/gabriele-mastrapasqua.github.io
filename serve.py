import livereload

import build


def rebuild():
    build.main()

rebuild()

server = livereload.Server()
server.setHeader("Cache-Control", "no-store")
server.watch("srcs/**/*.md", rebuild)
server.watch("srcs/**/*", rebuild)
server.watch("templates/**/*.html", rebuild)
server.watch("static/*.css", rebuild)
#server.watch("docs/static/**/*.js")
#server.watch("docs/static/**/*.css")
#server.watch("docs/static/**/*.png")
#server.watch("docs/static/**/*.jpg")
#server.watch("docs/**/*.html")
server.serve(root="docs")
