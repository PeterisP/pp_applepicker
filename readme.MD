1. Simple

Pull latest changes and build docker image

    $ ./update.sh

Run docker images

    $ ./run.sh



2. Or more detailed

    $ docker build -t pp_applepicker .

    $ docker run -it -p 6080:80 pp_applepicker

  Open [http://127.0.0.1:6080](http://127.0.0.1:6080)
