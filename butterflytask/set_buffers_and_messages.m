function set_buffers_and_messages

global exp

%% Clear all buffers
for buffer = 1:exp.numb_of_buffers
    clearpict(buffer)
end

%% Name buffers
exp.buffer.butterfly                    = 1;
exp.buffer.le_choice                    = 2;
exp.buffer.ri_choice                    = 3;
exp.buffer.break                        = 4; 
exp.buffer.after_break                  = 5;
exp.buffer.mem_oldnew                   = 6; % recall task
exp.buffer.mem_confidence               = 7; % recall task
exp.buffer.blank                        = 8; % also recall task?
exp.buffer.correct                      = 9;
exp.buffer.incorrect                    =10;
exp.buffer.wrong_key                    =11; % also recall task
exp.buffer.no_response                  =12; % also recall task
exp.buffer.response_reminder            =13; % also recall task
exp.buffer.butterfly_reminder           =14; % 
exp.buffer.instructions                 =15; % also recall task
exp.buffer.final                        =16; % also recall task


%% Buffers
preparestring('WRONG KEY (Use the A and B buttons)', exp.buffer.wrong_key);
preparestring('NO RESPONSE', exp.buffer.no_response);
preparestring('PLEASE RESPOND', exp.buffer.response_reminder);
preparestring('', exp.buffer.blank);
% Break buffers
break1 = 'Level COMPLETED!';
break2 = 'You can now take a 1 minute break!';
break3 = 'Stand up and walk around, but come back in time!';
preparestring(break1, exp.buffer.break, 0, 250);
preparestring(break2, exp.buffer.break);
preparestring(break3, exp.buffer.break, 0, -100); 

after_break1 = 'The break is over!';
after_break2 = ' ';
preparestring(after_break1, exp.buffer.after_break, 0, 250); 
preparestring(after_break2, exp.buffer.after_break); 
