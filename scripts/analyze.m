fle= fopen(['GeNNworkspace/results/' ...
	       '_dynamic_array_statemonitor_1_t'],'r');
t= fread(fle,'double');

V= loadResult(['GeNNworkspace/results/' ...
	       '_dynamic_array_statemonitor_1__recorded_v']);
fle= fopen(['cpp_standalone/results/' ...
	       '_dynamic_array_statemonitor_1_t'],'r');
t2= fread(fle,'double');
V2= loadResult(['cpp_standalone/results/' ...
	       '_dynamic_array_statemonitor_1__recorded_v']);
w= loadResult(['GeNNworkspace/results/' ...
	       '_dynamic_array_statemonitor__recorded_w']);
w2= loadResult(['cpp_standalone/results/' ...
	       '_dynamic_array_statemonitor__recorded_w']);

Apre= loadResult(['GeNNworkspace/results/' ...
	       '_dynamic_array_statemonitor_2__recorded_Apre']);
Apre2= loadResult(['cpp_standalone/results/' ...
	       '_dynamic_array_statemonitor_2__recorded_Apre']);

Apost= loadResult(['GeNNworkspace/results/' ...
	       '_dynamic_array_statemonitor_3__recorded_Apost']);
Apost2= loadResult(['cpp_standalone/results/' ...
	       '_dynamic_array_statemonitor_3__recorded_Apost']);

size(t)
size(t2)

%V= V(1:end-1,:);
%w= w(1:end-1,:);
%Apre= Apre(1:end-1,:);
%Apost= Apost(1:end-1,:);

for i=1:size(V,2)
  figure;
  plot(t,V(:,i));
  hold on;
  plot(t2,V2(:,i),'r');
  
  figure
  plot(t,w(:,i));
  hold on;
  plot(t2,w2(:,i),'r');

  figure
  plot(t,Apre(:,i));
  hold on;
  plot(t2,Apre2(:,i),'r');
  plot(t,Apost(:,i),'-.');
  plot(t2,Apost2(:,i),'-.r');
end

size(V)
size(V2)
size(w)
size(w2)


dV= abs(V-V2);
dfV= find(dv ~= 0);
dw= abs(w-w2);
dfw= find(dw ~= 0);

dfV(:,1)
dfw(:,1)
