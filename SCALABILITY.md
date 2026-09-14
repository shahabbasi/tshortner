# Scalability

## Question 1: What if this is going to be a multi instance application?

Already supported! However, it can be perfected if fails load tests which I believe it won't (We can discuss this in the interview session).

## Question 2: What should we do to prevent downtime in terms of heavy load peaks?

1. We should separete read and write instances so high load on each won't affect the other one. Specially high write load should not prevent existing shortlinks to work.

2. We should use a clustered database.

3. If we can affort shortlinks to be available after a while, we can even queue shortlink create requests on Kafka to be able to manage back pressure on writes so we can easily scale our database cluster with multiple nodes.

## Taking scaleability even further (Not exactly asked but I guess you want me to mention this)

What is very very important is what happens if we need to really scale like 1000 instances? or 10_000? or event 1 Million? I mean the current design will normally cover 99% of scenarios but let's say it will hit the limit in terms of scale. What happens then?

Here I want to answer that!

Well, we have a thousand ways to reach real scaleability (As the guy in movie Marmoolak says "There are as many ways to reach God as all human population") so I won't mention all. There are some which I think are good approaches which I will mention bellow.

1. Sharding the database. This will work like partitioning a Kafka topic. So each database shard is responsible for a set of prefixes and the instances know which one to call based on their own assigned prefixes. If we do this, we won't be only sharding the data so the database can perform better. This way, we will split the load between the databases and instances and not every instance access every shard! This is a complicated solution that needs a routing / prefix management so we can assign prefixes to instances dynamically and also route each request to responsible instance.

2.Having completely isolated websites! Sounds kind of dumb but let's think outside the box. We can have `bit.ly` as main domain and also these as subs: `bi1.ly, bi2.ly, bi3.ly` etc. You might be wondering how that might help! We will direct users to one of those by a round robin strategy instead of generating all short links as `bit.ly/link`. When a user comes with bit.ly domain or opens one of those without the shortened url like `https://bi1.ly/`, we will just randomly route them to one of our active domains and the generated link will stay there inside an isolated database and etc. We can also think about gathering analytical data in one place later. Also with this approach, whenevery we see that we're hitting the limit and need more scale, we can just add some more domains.


## Notes

- I used Redis pub / sub here to reduce development time. In normal case, I would've used Kafka here to ensure persistence besides scalability.

- For analytical data processing I used Redis to delivery messages which results in high message drop rate (~= 1 - 1 / instance_count) but we can also use Kafka here and use the prefix as key of message which will result in prefixes to be distibuted among instances instead of dropping unrelated messages.

