
// scalar can be any scalar type such as float, double

template class scalar
void convert_dynamic_arrays_2_dense_matrix(vector<int32> &source, vector<int32> &target, vector<scalar> &gvector, scalar *g, int srcNN, int trgNN)
{
    assert(source.size() == target.size());
    assert(source.size() == gvector.size());
    unsigned int size= source.size; 
    for (int s= 0; s < srcNN; s++) {
	for (int t= 0; t < trgNN; t++) {
	    g[s*trgNN+t]= (scalar) 0.0;
	}
    }
    for (int i= 0; i < size; i++) {
	assert(source[i]-1 < srcNN);
	assert(target[i]-1 < trgNN);
	g[(source[i]-1)*trgNN+target[i]-1]= gvector[i];
    }
}

void convert_dynamic_arrays_2_sparse_synapses(vector<int32> source, vector<int32> target, vector<scalar> gvector, sparseStruct &c, int srcNN, int trgNN)
{
    assert(source.size() == target.size());
    assert(source.size() == gvector.size());
    // create a list of the postsynaptic targets ordered by presynaptic sources
    vector<vector<int32> > bypre(srcNN);
    unsigned int size= source.size; 
    for (int i= 0; i < size; i++) {
	assert(source[i]-1 < srcNN);
	assert(target[i]-1 < trgNN);
	bypre[source[i]-1].push_back(target[i]-1);
	bypreG[source[i]-1].push_back(gvector[i]);
    }
    // convert this intermediate representation into the sparse synapses struct
    c.connN= source.size();
    allocateSparseArray(&c, srcNN, false);
    unsigned int cnt= 0;
    for (int i= 0; i < srcNN; i++) {
	size= bypre[i].size();
	c.gIndInG[i]= cnt; 
	for (int j= 0; j < size; i++) {
	    c.gInd[cnt]= bypre[i][j];
	    c.gp[cnt++]= bypreG[i][j];
	}
    }
    c.gIndInG[srcNN]= cnt;
}
