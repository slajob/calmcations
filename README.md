# calmcations

This concept was developed as part of the [hackyeah 2025](https://hackyeah.pl) hackaton.

> Reimagine the way we explore the world! Whether it’s making travel safer, more sustainable,
> or simply more enjoyable, we want to see your best ideas in action. Consider how
> technology can address the rising trend of "calmcations", find a way that helps travelers
> recharge, design a platform for meaningful cultural exchanges, or a new way to navigate
> cities stress-free. From eco-friendly trip planning to smarter safety solutions, show us how
> your idea can make travel more enriching and hassle-free for everyone.


## TODO

- [ ] user actions
	- [x] create new point
	- [ ] checkin existing point
		- [x] create checkin
		- [x] tag:
	- [ ] query nearby points
		- [ ] sorting them by
		    - [ ] tag
		- [ ] query by location (not to load all of them)
    - [x] load fixtures


## preload fixtures

The algorithm proposed recommend spots based on previous users checkins.

To meaningfully use this app you should upload some data.

You can do so by running:
```
 curl -X POST \
 0.0.0.0:20778/api/mock-data \
 -H "Content-Type: application/json" \
 --data-binary @mock_data.json
```
