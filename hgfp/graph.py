import dgl
import torch
from rdkit import Chem


HYBRIDIZATION = {
    Chem.rdchem.HybridizationType.SP: torch.tensor([1, 0, 0, 0, 0], dtype=torch.float32),
    Chem.rdchem.HybridizationType.SP2: torch.tensor([0, 1, 0, 0, 0], dtype=torch.float32),
    Chem.rdchem.HybridizationType.SP3: torch.tensor([0, 0, 1, 0, 0], dtype=torch.float32),
    Chem.rdchem.HybridizationType.SP3D: torch.tensor([0, 0, 0, 1, 0], dtype=torch.float32),
    Chem.rdchem.HybridizationType.SP3D2: torch.tensor([0, 0, 0, 0, 1], dtype=torch.float32),
    Chem.rdchem.HybridizationType.S: torch.tensor([0, 0, 0, 0, 0], dtype=torch.float32)
}

def fp(atom):
    return torch.cat(
        [
            torch.tensor(
                [
                    atom.GetTotalDegree(),
                    atom.GetTotalValence(),
                    atom.GetTotalValence(),
                    atom.GetFormalCharge(),
                    atom.GetIsAromatic() * 1.0,
                    atom.GetMass(),
                    atom.IsInRingSize(3) * 1.0,
                    atom.IsInRingSize(4) * 1.0,
                    atom.IsInRingSize(5) * 1.0,
                    atom.IsInRingSize(6) * 1.0,
                    atom.IsInRingSize(7) * 1.0,
                    atom.IsInRingSize(8) * 1.0,
                ],
                dtype=torch.float32),
            HYBRIDIZATION[atom.GetHybridization()]
        ],
        dim=0)

def from_rdkit_mol(mol):
    # initialize graph
    g = dgl.DGLGraph()

    # enter nodes
    n_atoms = mol.GetNumAtoms()
    g.add_nodes(n_atoms)
    g.ndata['type'] = torch.Tensor(
        [[atom.GetAtomicNum()] for atom in mol.GetAtoms()])

    h_v =  torch.zeros(
        g.ndata['type'].shape[0], 100, dtype=torch.float32)

    h_v[
        torch.arange(g.ndata['type'].shape[0]),
        torch.squeeze(g.ndata['type']).long()] = 1.0

    h_v_fp = torch.stack(
        [fp(atom) for atom in mol.GetAtoms()],
        axis=0)

    h_v = torch.cat(
        [
            h_v,
            h_v_fp
        ],
        dim=-1) # (n_atoms, 117)

    g.ndata['h0'] = h_v

    try:
        # enter xyz in if there is conformer
        conformer = mol.GetConformer()
        g.ndata['xyz'] = torch.Tensor(
            [
                [
                    conformer.GetAtomPosition(idx).x,
                    conformer.GetAtomPosition(idx).y,
                    conformer.GetAtomPosition(idx).z
                ] for idx in range(n_atoms)
            ])
    except:
        pass

    # enter bonds
    bonds = list(mol.GetBonds())
    bonds_begin_idxs = [bond.GetBeginAtomIdx() for bond in bonds]
    bonds_end_idxs = [bond.GetEndAtomIdx() for bond in bonds]
    bonds_types = [bond.GetBondType().real for bond in bonds]

    # NOTE: dgl edges are directional
    g.add_edges(bonds_begin_idxs, bonds_end_idxs)
    g.add_edges(bonds_end_idxs, bonds_begin_idxs)

    g.edata['type'] = torch.Tensor(bonds_types)[:, None].repeat(2, 1)

    return g
