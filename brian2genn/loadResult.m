function d= loadResult(name)
fle= fopen(name,'r');
d= fread(fle,'double');
d= reshape(d,10,length(d)/10);
d= d';
fclose(fle);