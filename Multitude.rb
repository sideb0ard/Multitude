#!/usr/bin/ruby -w
require 'rubygems' # not necessary with ruby 1.9 but included for completeness
require 'twilio-ruby'

# put your own credentials here
account_sid = 'ACbeaca99a906b6b3d8b9581c25ce5a16f'
auth_token = '443c64e732a60cc75722dc7a8ba8e34a'

# set up a client to talk to the Twilio REST API
@client = Twilio::REST::Client.new account_sid, auth_token

# send an sms
@client.account.sms.messages.create(
  :from => '+14155992671',
  :to => '+14157455030',
  :body => 'boo ya!!'
)
