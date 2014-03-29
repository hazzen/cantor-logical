import sys
import pick
import twitter
import ConfigParser

if __name__ == '__main__':
  tweet = pick.GetMeATweet()
  if not tweet:
    sys.exit(1)

  config = ConfigParser.ConfigParser()
  config.read('post.cfg')
  consumer_key = config.get('Twitter', 'consumer_key')
  consumer_secret = config.get('Twitter', 'consumer_secret')
  access_token_key = config.get('Twitter', 'access_token_key')
  access_token_secret = config.get('Twitter', 'access_token_secret')

  api = twitter.Api(
      consumer_key=consumer_key,
      consumer_secret=consumer_secret,
      access_token_key=access_token_key,
      access_token_secret=access_token_secret,
  )
  found = raw_input('Going to tweet:\n%s\n(ctrl-c to cancel)\n' % tweet)
  api.PostUpdate(tweet)
  pick.WriteBlacklist()
