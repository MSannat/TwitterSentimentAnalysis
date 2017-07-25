library('ggplot2')

#-----------------------------------------------------------
#
#   Sentiment score bar chart for candidates

#
#-----------------------------------------------------------


library('ggplot2')
w205 <- read.csv(file='./results.csv',sep=',',header=T)
str(w205)
w205.new <- melt(w205,id.vars="States")
names(w205.new)=c("States","Sentiments", "value" )

avg.ratings.plot <- ggplot(w205.new, aes(x=States,y=value,fill=Sentiments))+ geom_bar(stat="identity",position="dodge")   + labs(x="States", y="Sentiments", title=" Tweet sentiments for Hillary Clinton and Donald Trump in CA and TX")
avg.ratings.plot <-avg.ratings.plot+theme(axis.text=element_text(size=12), axis.title=element_text(size=14,face="bold"))
avg.ratings.plot <- avg.ratings.plot + ggtitle("Tweet sentiments for Hillary Clinton and Donald Trump in CA and TX") + theme(plot.title = element_text(lineheight=3, face="bold", color="black", size=29))
avg.ratings.plot <- avg.ratings.plot + theme(axis.title.y = element_text(size = rel(1.8), angle = 90))
avg.ratings.plot <- avg.ratings.plot + theme(axis.title.x = element_text(size = rel(1.8), angle = 00))
avg.ratings.plot <- avg.ratings.plot+ theme(legend.text=element_text(size=12)) + theme(legend.title=element_text(size=15))
avg.ratings.plot