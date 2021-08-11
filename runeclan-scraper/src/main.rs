use clap::{App, AppSettings, Arg};
use futures::{
    stream,
    Stream, StreamExt,
};
use indicatif::{ProgressStyle, ProgressBar};
use linecount::count_lines;
use reqwest::Client;
use soup::prelude::*;
use std::fmt::Display;
use std::fs::File;
use std::io::{self, BufRead};
use std::{rc::Rc, sync::Arc, sync::Mutex, time::Instant};
use tokio;
type Error = Box<dyn std::error::Error + 'static>;

#[derive(Debug)]
struct UserInfo {
    name: Option<String>,
    xp: Option<u64>,
    date: Option<String>,
    previous_names: Option<Vec<String>>,
}

impl Display for UserInfo {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let n = &"None".to_string();
        let empty = vec![];
        let name = self.name.as_ref().unwrap_or(n);
        let date = self.date.as_ref().unwrap_or(n);
        let xp = self.xp.as_ref().map(|f|f.to_string()).unwrap_or("None".to_string());
        let names = self.previous_names.as_ref().unwrap_or(&empty);

        write!(f, "{} - {} - {} - {:?}", name, date, xp, names)
    }
}
fn parse<'a>(
    client: Arc<Client>,
    max_concurrent: usize,
    urls: impl Iterator<Item = String> + 'static,
) -> impl Stream<Item = Result<UserInfo, Error>> + 'a {
    let bodies = stream::iter(urls)
        .map(move |url| {
            let client = client.clone();
            async move {
                let resp = client.get(url).send().await?;
                let text = resp.text().await?;
                let soup = Soup::new(&text);

                let name = soup
                    .tag("span")
                    .class("xp_tracker_hname")
                    .find()
                    .and_then(|v| Some(v.text()));
                let date = soup
                    .tag("div")
                    .class("xp_tracker_activity_r")
                    .find()
                    .and_then(|v| Some(v.text()));
                let xp = soup.tag("td").class("xp_tracker_cxp").find().and_then(|v| {
                    let mut text = v.text();
                    text.retain(|c| c != ',');
                    Some(text.parse::<u64>().unwrap())
                });
                let previous = soup
                    .tag("div")
                    .class("xp_tracker_prevnames")
                    .find()
                    .and_then(|v| {
                        let mut text = v.text();
                        text = text.strip_prefix("Previous Names: ")?.to_string();

                        Some(text.split(",").map(|s| s.to_string()).collect())
                    });

                Ok(UserInfo {
                    name,
                    date,
                    xp,
                    previous_names: previous,
                })
            }
        })
        .buffered(max_concurrent);

    Box::new(bodies)
}

async fn output_parsed<'a>(values: u64, stream: impl Stream<Item = Result<UserInfo, Error>> + 'a) {
    let mut last_user = Instant::now();
    let mut count = 0;
    let mut total_seconds = 0;
    let concurrent_no = Rc::new(Mutex::new(0));

    let sty = ProgressStyle::default_bar()
        .template("[{elapsed_precise}] {bar:40.cyan/blue} {pos:>7}/{len:7} {msg}")
        .progress_chars("##-");

    let pb = ProgressBar::new(values);
    pb.set_style(sty);

    pb.enable_steady_tick(1000);

    stream
        .for_each(|b| {
            pb.inc(1);

            let now = Instant::now();
            total_seconds += (now - last_user).as_millis();
            count += 1;

            pb.set_message(format!("Average Time Per User: {}", total_seconds / count));
            last_user = now;

            let concurrent_no = Rc::clone(&concurrent_no);
            async move {
                match b {
                    Ok(user) => {
                        let mut cn = concurrent_no.lock().unwrap();
                        if let None = user.name {
                            *cn += 1;

                            if *cn > 10 {
                                eprintln!("10 Consecutive Pages without data, exiting...");
                                std::process::exit(0);
                            }
                        } else {
                            println!("{}", user);

                            if *cn != 0 {
                                *cn = 0;
                            }
                        }
                    }
                    Err(_) => (),
                }
            }
        })
        .await;

    pb.finish_with_message(format!(
        "Total MS: {} Count: {} Average MS: {}",
        total_seconds,
        count,
        total_seconds / count
    ));
}

#[tokio::main]
async fn main() {
    let matches = App::new("Runeclan Scraper")
        .version("1.0")
        .author("Davis Schenkenberger <davisschenk@gmail.com>")
        .about("Scrapes data from runeclan")
        .setting(AppSettings::ArgRequiredElseHelp)
        .subcommand(
            App::new("by_id")
                .about("Scrape user data by uid")
                .arg(
                    Arg::new("min")
                        .long("min")
                        .takes_value(true)
                        .required(false),
                )
                .arg(
                    Arg::new("max")
                        .long("max")
                        .takes_value(true)
                        .required(false),
                ),
        )
        .subcommand(
            App::new("by_name").about("Scrape user data by name").arg(
                Arg::new("file")
                    .value_name("FILE")
                    .takes_value(true)
                    .required(true),
            ),
        )
        .get_matches();

    let client = Arc::new(Client::new());

    if let Some(ref matches) = matches.subcommand_matches("by_name") {
        let file = File::open(matches.value_of("file").unwrap()).unwrap();
        let lines = io::BufReader::new(file).lines();

        let bodies = parse(
            client,
            50,
            lines.map(|f| format!("https://www.runeclan.com/user/{}", f.unwrap())),
        );

        let file = File::open(matches.value_of("file").unwrap()).unwrap();
        output_parsed(count_lines(file).unwrap() as u64 + 1, bodies).await;
    } else if let Some(ref matches) = matches.subcommand_matches("by_id") {
        let min = matches
            .value_of("min")
            .unwrap_or("1")
            .parse::<u64>()
            .unwrap();
        let max = matches.value_of("max");

        match max {
            Some(n) => {
                let m = n.parse::<u64>().unwrap();
                output_parsed(
                    m - min + 1,
                    parse(
                        client,
                        50,
                        (min..=m).map(|f| format!("https://www.runeclan.com/uid/{}", f)),
                    ),
                )
                .await;
            }
            None => {
                output_parsed(
                    819864,
                    parse(
                        client,
                        50,
                        (min..).map(|f| format!("https://www.runeclan.com/uid/{}", f)),
                    ),
                )
                .await;
            }
        };
    }
}
