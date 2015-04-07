
// scalar can be any scalar type such as float, double
#include <stdint.h>

#ifndef CONVERT_SYNAPSES
#define CONVERT_SYNAPSES

template<class scalar>
void convert_dynamic_arrays_2_dense_matrix(vector<int32_t> &source, vector<int32_t> &target, vector<scalar> &gvector, scalar *g, int srcNN, int trgNN)
{
    assert(source.size() == target.size());
    assert(source.size() == gvector.size());
    unsigned int size= source.size(); 
    for (int s= 0; s < srcNN; s++) {
	for (int t= 0; t < trgNN; t++) {
	    g[s*trgNN+t]= (scalar) 0.0;
	}
    }
//    cerr << size << "!!!!!!" << endl;
    for (int i= 0; i < size; i++) {
	assert(source[i] < srcNN);
	assert(target[i] < trgNN);
//	cerr << source[i] << " " << target[i] << " " << gvector[i] << endl;
	g[source[i]*trgNN+target[i]]= gvector[i];
    }
//    cerr << endl;
//    cerr << "-------------------------";
}

template<class scalar>
void convert_dynamic_arrays_2_sparse_synapses(vector<int32_t> source, vector<int32_t> target, vector<scalar> gvector, Conductance &c, int srcNN, int trgNN)
{
    assert(source.size() == target.size());
    assert(source.size() == gvector.size());
    // create a list of the postsynaptic targets ordered by presynaptic sources
    vector<vector<int32_t> > bypre(srcNN);
    vector<vector<int32_t> > bypreG(srcNN);
    unsigned int size= source.size(); 
    for (int i= 0; i < size; i++) {
	assert(source[i] < srcNN);
	assert(target[i] < trgNN);
	bypre[source[i]].push_back(target[i]);
	bypreG[source[i]].push_back(gvector[i]);
    }
    // convert this intermediate representation into the sparse synapses struct
    unsigned int cnt= 0;
    for (int i= 0; i < srcNN; i++) {
	size= bypre[i].size();
	c.indInG[i]= cnt; 
	for (int j= 0; j < size; i++) {
	    c.ind[cnt]= bypre[i][j];
	}
    }
    c.indInG[srcNN]= cnt;
}

template<class scalar>
void convert_dense_matrix_2_dynamic_arrays(scalar *g, int srcNN, int trgNN, vector<int32_t> &source, vector<int32_t> &target, vector<scalar> &gvector)
{
    assert(source.size() == target.size());
    assert(source.size() == gvector.size());
    unsigned int size= source.size(); 
    for (int i= 0; i < size; i++) {
	assert(source[i] < srcNN);
	assert(target[i] < trgNN);
	gvector[i]= g[source[i]*trgNN+target[i]];
    }
}

template<class scalar>
void convert_dynamic_arrays_2_sparse_synapses(Conductance &c, int srcNN, int trgNN, vector<int32_t> source, vector<int32_t> target, vector<scalar> gvector)
{
    assert(source.size() == target.size());
    assert(source.size() == gvector.size());
    // create a list of the postsynaptic targets ordered by presynaptic sources
    vector<vector<int32_t> > bypre(srcNN);
    vector<vector<int32_t> > bypreG(srcNN);
    for (int i= 0; i < srcNN; i++) {
	for (int j= c.indInG[i]; j < c.indInG[i+1]; j++) {
	    bypre[i].push_back(c.ind[j]);
	}
    }
    // convert this intermediate representation into the brian arrays
    unsigned int cnt= 0;
    for (int i= 0; i < source.size(); i++) {
	vector<int32_t>::iterator pos;
	vector<int32_t> &vec= bypre[source[i]];
	pos= find(vec.begin(), vec.end(), target[i]);
	if (pos != vec.end()) {
	    int index= pos - vec.begin();
	    gvector[i]= bypreG[source[i]][index];
	}
	else {
	    cerr << "sparse matrix to brian lists conversion error ... exiting." << endl;
	    exit(1);
	}
    }
}

void create_hidden_weightmatrix(vector<int32_t> &source, vector<int32_t> &target, char* hwm, int srcNN, int trgNN)
{
    for (int s= 0; s < srcNN; s++) {
	for (int t= 0; t < trgNN; t++) {
	    hwm[s*trgNN+t]= 0;
	}
    }
    for (int i= 0; i < source.size(); i++) {
	hwm[source[i]*trgNN+target[i]]= 1;
    }
}
#endif
